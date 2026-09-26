from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import func, select

from marcus.catalog.api import basic_list
from marcus.community.content_common import author_summary, links_response, reactions, visible
from marcus.contracts import responses as out
from marcus.contracts import schemas as s
from marcus.core.common import (
    audit,
    city_exists,
    current_user,
    data,
    editor,
    enqueue,
    fail,
    get,
    idempotency,
    page,
    remember,
    version,
)
from marcus.core.db import get_session
from marcus.core.security import now
from marcus.database import models as m
from marcus.editorials.document import validate_document
from marcus.media.api import media_response, validate_assets

router = APIRouter(tags=["editorials"])


async def article_draft_response(db, a):
    d = await get(db, m.EditorDraft, a.id)
    out = data(d)
    latest = await db.scalar(
        select(m.EditorRevision)
        .where(m.EditorRevision.article_id == a.id)
        .order_by(m.EditorRevision.revision_no.desc())
        .limit(1)
    )
    _, media = validate_document(d.document)
    ids = set(media) | ({d.cover_asset_id} if d.cover_asset_id else set())
    out.update(
        published_revision_id=a.published_revision_id,
        latest_submission=data(latest) if latest else None,
        media=[await media_response(db, await get(db, m.MediaAsset, id)) for id in ids],
    )
    return out


async def focus(db, city_id, obj, strict=False):
    if obj.focus_type is None:
        if strict or obj.primary_place_id or obj.primary_event_id:
            fail(422, "focus_required")
        return None
    if obj.focus_type == "place":
        if obj.primary_event_id:
            fail(422, "focus_mismatch")
        if not obj.primary_place_id:
            if strict:
                fail(422, "place_required")
            return None
        p = await get(db, m.Place, obj.primary_place_id)
        if p.city_id != city_id or (strict and p.status != "active"):
            fail(422, "invalid_primary_place")
        return p.district_id
    if obj.primary_place_id:
        fail(422, "focus_mismatch")
    if not obj.primary_event_id:
        if strict:
            fail(422, "event_required")
        return None
    e = await get(db, m.Event, obj.primary_event_id)
    if e.city_id != city_id or (strict and e.status != "published"):
        fail(422, "invalid_primary_event")
    if e.place_id:
        p = await get(db, m.Place, e.place_id)
        if p.city_id != city_id or (strict and p.status != "active"):
            fail(422, "invalid_event_place")
        return p.district_id
    return None


async def article_validate(db, a, d, user, strict):
    try:
        plain, media = validate_document(d.document)
    except (ValueError, TypeError, KeyError, AttributeError):
        fail(422, "invalid_document")
    district = await focus(db, a.city_id, d, strict)
    if strict and (not d.title.strip() or not plain.strip()):
        fail(422, "article_empty")
    await validate_assets(db, user, list(media), "editorial_media", strict, media)
    if d.cover_asset_id:
        await validate_assets(
            db, user, [d.cover_asset_id], "editorial_media", strict, {d.cover_asset_id: "image"}
        )
    return plain, media, district


async def article_response(db, a, user):
    r = await get(db, m.EditorRevision, a.published_revision_id)
    result = {
        k: getattr(r, k)
        for k in ["title", "subtitle", "summary", "focus_type", "document", "document_schema_version"]
    }
    result.update(await links_response(db, r.primary_place_id, r.primary_event_id))
    tags = (
        await db.scalars(
            select(m.Tag)
            .join(m.EditorRevisionTag, m.EditorRevisionTag.tag_id == m.Tag.id)
            .where(m.EditorRevisionTag.revision_id == r.id)
        )
    ).all()
    assets = (
        await db.scalars(
            select(m.MediaAsset)
            .join(m.EditorRevisionAsset, m.EditorRevisionAsset.asset_id == m.MediaAsset.id)
            .where(m.EditorRevisionAsset.revision_id == r.id)
            .distinct()
        )
    ).all()
    result.update(
        id=a.id,
        revision_id=r.id,
        kind="editorial",
        cover=await media_response(db, await db.get(m.MediaAsset, r.cover_asset_id))
        if r.cover_asset_id
        else None,
        media=[await media_response(db, x) for x in assets],
        tags=[data(t) for t in tags],
        editor=await author_summary(db, a.author_id),
        city=data(await get(db, m.City, a.city_id)),
        district=data(await get(db, m.District, a.district_id)) if a.district_id else None,
        first_published_at=a.first_published_at,
        published_at=a.published_at,
        reactions=await reactions(db, a.id, user, True),
    )
    return result


@router.get("/editorials/{id}", response_model=out.Editorial)
async def read(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    a = await get(db, m.EditorArticle, id)
    await visible(db, a, user)
    return await article_response(db, a, user)


@router.get("/admin/editorials")
async def admin_list(
    city_id: str | None = None,
    district_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    filters = [m.EditorArticle.status != "deleted"]
    if city_id:
        filters.append(m.EditorArticle.city_id == city_id)
    if district_id:
        district = await get(db, m.District, district_id)
        if city_id and district.city_id != city_id:
            fail(422, "district_city_mismatch")
        filters.append(m.EditorArticle.district_id == district_id)
    rows, nxt = await basic_list(
        db, m.EditorArticle, limit, cursor, filters, "admin_articles:" + str(city_id) + ":" + str(district_id)
    )
    items = []
    for row in rows:
        d = await get(db, m.EditorDraft, row.id)
        items.append(
            {
                **data(row),
                "title": d.title,
                "focus_type": d.focus_type,
                "district": data(await get(db, m.District, row.district_id)) if row.district_id else None,
            }
        )
    return page(items, nxt)


@router.post("/admin/editorials", status_code=201)
async def create(
    body: s.CreateEditorial,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    rec, h = await idempotency(db, user, "create_editorial", idempotency_key, body.model_dump())
    if rec:
        return await article_draft_response(db, await get(db, m.EditorArticle, rec.resource_id))
    await city_exists(db, body.city_id)
    if body.district_id and (await get(db, m.District, body.district_id)).city_id != body.city_id:
        fail(422, "district_city_mismatch")
    a = m.EditorArticle(author_id=user.id, city_id=body.city_id, district_id=body.district_id)
    db.add(a)
    await db.flush()
    db.add(m.EditorDraft(article_id=a.id, last_edited_by=user.id))
    await db.flush()
    await remember(db, user, "create_editorial", idempotency_key, h, a.id, 201)
    return await article_draft_response(db, a)


@router.get("/admin/editorials/{id}/draft")
async def draft(id: str, user=Depends(editor), db=Depends(get_session, scope="function")):
    a = await get(db, m.EditorArticle, id)
    if a.status == "deleted":
        fail(404, "not_found")
    return await article_draft_response(db, a)


@router.patch("/admin/editorials/{id}/draft")
async def save(
    id: str, body: s.EditorialDraftInput, user=Depends(editor), db=Depends(get_session, scope="function")
):
    a = await get(db, m.EditorArticle, id, True)
    if a.status == "deleted":
        fail(404, "not_found")
    d = await get(db, m.EditorDraft, id, True)
    version(d, body.expected_version, "edit_version")
    for k, v in body.model_dump(exclude_unset=True, exclude={"expected_version"}).items():
        setattr(d, k, v)
    await article_validate(db, a, d, user, False)
    for id in d.tag_ids:
        await get(db, m.Tag, id)
    d.edit_version += 1
    d.last_edited_by = user.id
    await db.flush()
    return await article_draft_response(db, a)


async def publish_result(db, r):
    review = await db.scalar(
        select(m.EditorReview).where(m.EditorReview.revision_id == r.id).with_for_update()
    )
    job = await db.scalar(
        select(m.Job).where(m.Job.dedupe_key == "review_editorial:" + review.id).with_for_update()
    )
    return {
        "article_id": r.article_id,
        "revision_id": r.id,
        "review_status": review.status,
        "job_id": job.id if job else None,
    }


@router.post("/admin/editorials/{id}/publish", status_code=202)
async def publish(
    id: str,
    body: s.PublishInput,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    operation = "publish_editorial:" + id
    rec, h = await idempotency(db, user, operation, idempotency_key, body.model_dump())
    if rec:
        return await publish_result(db, await get(db, m.EditorRevision, rec.resource_id, True))
    a = await get(db, m.EditorArticle, id, True)
    if a.status in ("hidden", "deleted"):
        fail(409, "article_unavailable")
    d = await get(db, m.EditorDraft, id, True)
    version(d, body.expected_edit_version, "edit_version")
    r = await db.scalar(
        select(m.EditorRevision)
        .where(m.EditorRevision.article_id == id, m.EditorRevision.based_on_edit_version == d.edit_version)
        .with_for_update()
    )
    if not r:
        plain, media, _ = await article_validate(db, a, d, user, True)
        for tid in d.tag_ids:
            if not (await get(db, m.Tag, tid)).enabled:
                fail(422, "tag_disabled")
        number = (
            await db.scalar(
                select(func.max(m.EditorRevision.revision_no)).where(m.EditorRevision.article_id == id)
            )
            or 0
        ) + 1
        r = m.EditorRevision(
            article_id=id,
            revision_no=number,
            based_on_edit_version=d.edit_version,
            submitted_by=user.id,
            plain_text=plain,
            **{
                k: getattr(d, k)
                for k in [
                    "title",
                    "subtitle",
                    "summary",
                    "focus_type",
                    "primary_place_id",
                    "primary_event_id",
                    "document",
                    "document_schema_version",
                    "cover_asset_id",
                ]
            },
        )
        r.summary = r.summary.strip() or plain[:500]
        db.add(r)
        await db.flush()
        for tid in d.tag_ids:
            db.add(m.EditorRevisionTag(revision_id=r.id, tag_id=tid))
        for aid in media:
            db.add(m.EditorRevisionAsset(revision_id=r.id, asset_id=aid, role="inline"))
        if r.cover_asset_id:
            db.add(m.EditorRevisionAsset(revision_id=r.id, asset_id=r.cover_asset_id, role="cover"))
        review = m.EditorReview(revision_id=r.id)
        db.add(review)
        await db.flush()
        await enqueue(db, "review_editorial", review.id, {"revision_id": r.id})
    await remember(db, user, operation, idempotency_key, h, r.id, 202)
    return await publish_result(db, r)


@router.get("/admin/editorials/{id}/publication")
async def publication(id: str, user=Depends(editor), db=Depends(get_session, scope="function")):
    a = await get(db, m.EditorArticle, id)
    r = await db.scalar(
        select(m.EditorRevision)
        .where(m.EditorRevision.article_id == id)
        .order_by(m.EditorRevision.revision_no.desc())
        .limit(1)
    )
    review = (
        await db.scalar(select(m.EditorReview).where(m.EditorReview.revision_id == r.id).with_for_update())
        if r
        else None
    )
    return {
        "revision_id": r.id if r else None,
        "review_status": review.status if review else None,
        "is_current_published": bool(r and a.status == "published" and a.published_revision_id == r.id),
        "reason_code": review.reason_code if review else None,
    }


@router.patch("/admin/editorials/{id}")
async def settings_update(
    id: str,
    body: s.ArticleSettingsInput,
    request: Request,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    a = await get(db, m.EditorArticle, id, True)
    version(a, body.expected_version)
    a.editorial_rank = body.editorial_rank
    a.version += 1
    await audit(db, request, user, "rank_editorial", "editor_article", id)
    return data(a)


async def apply_revision(db, a, r):
    author = await get(db, m.User, a.author_id)
    if author.status != "active":
        fail(409, "author_inactive")
    submitting = await get(db, m.User, r.submitted_by)
    _, _, district = await article_validate(db, a, r, submitting, True)
    a.status = "published"
    a.published_revision_id = r.id
    a.district_id = district
    a.first_published_at = a.first_published_at or now()
    a.published_at = now()
    a.version += 1

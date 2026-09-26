from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import delete, func, select

from marcus.catalog.api import basic_list
from marcus.community.content_common import author_summary, links_response, note_links, reactions, visible
from marcus.contracts import responses as out
from marcus.contracts import schemas as s
from marcus.core.common import (
    city_exists,
    current_user,
    data,
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
from marcus.media.api import media_response, validate_assets

router = APIRouter(tags=["notes"])


async def own(db, id, user, lock=False):
    n = await get(db, m.Note, id, lock)
    if n.author_id != user.id or n.status == "deleted":
        fail(404, "not_found")
    return n


async def note_response(db, n, user):
    images = (
        await db.scalars(
            select(m.MediaAsset)
            .join(m.NoteImage, m.NoteImage.asset_id == m.MediaAsset.id)
            .where(m.NoteImage.note_id == n.id)
            .order_by(m.NoteImage.position)
        )
    ).all()
    images = [await media_response(db, a) for a in images]
    result = {
        k: getattr(n, k)
        for k in [
            "id",
            "title",
            "body_text",
            "first_published_at",
            "published_at",
            "published_submission_id",
            "version",
        ]
    }
    result.update(
        kind="note",
        images=images,
        cover=images[0] if images else None,
        author=await author_summary(db, n.author_id),
        city=data(await get(db, m.City, n.city_id)),
        reactions=await reactions(db, n.id, user),
    )
    result.update(await links_response(db, n.place_id, n.event_id))
    return result


async def latest_submission(db, id):
    return await db.scalar(
        select(m.NoteSubmission)
        .where(m.NoteSubmission.note_id == id)
        .order_by(m.NoteSubmission.submission_no.desc())
        .limit(1)
    )


async def draft_response(db, n):
    d = await get(db, m.NoteDraft, n.id)
    out = data(d)
    latest = await latest_submission(db, n.id)
    out.update(
        version=n.version,
        latest_submission=(
            {**data(latest), "review_status": latest.status, "submission_id": latest.id} if latest else None
        ),
        media=[await media_response(db, await get(db, m.MediaAsset, id)) for id in d.image_ids],
    )
    return out


@router.post("/notes", status_code=201, response_model=out.NoteDraft)
async def create(
    body: s.CreateContent,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    record, h = await idempotency(db, user, "create_note", idempotency_key, body.model_dump())
    if record:
        return await draft_response(db, await own(db, record.resource_id, user))
    await city_exists(db, body.city_id)
    n = m.Note(author_id=user.id, city_id=body.city_id)
    db.add(n)
    await db.flush()
    db.add(m.NoteDraft(note_id=n.id))
    await db.flush()
    await remember(db, user, "create_note", idempotency_key, h, n.id, 201)
    return await draft_response(db, n)


@router.get("/notes/{id}", response_model=out.Note)
async def read(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    n = await get(db, m.Note, id)
    await visible(db, n, user)
    return await note_response(db, n, user)


@router.get("/notes/{id}/draft", response_model=out.NoteDraft)
async def draft(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await draft_response(db, await own(db, id, user))


@router.patch("/notes/{id}/draft", response_model=out.NoteDraft)
async def save(
    id: str, body: s.NoteDraftInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    n = await own(db, id, user, True)
    d = await get(db, m.NoteDraft, id, True)
    version(d, body.expected_version, "edit_version")
    for k, v in body.model_dump(exclude_unset=True, exclude={"expected_version"}).items():
        setattr(d, k, v)
    d.place_id = await note_links(db, n.city_id, d.place_id, d.event_id)
    await validate_assets(db, user, d.image_ids, "note_image")
    d.edit_version += 1
    await db.flush()
    return await draft_response(db, n)


async def validate_submission(db, n, submission):
    if not submission.body_text.strip() and not submission.image_ids:
        fail(422, "note_empty")
    author = await get(db, m.User, n.author_id)
    if author.status != "active":
        fail(409, "author_inactive")
    # Historical snapshot may have an old venue after an event moves; validate the current event link.
    await note_links(db, n.city_id, submission.place_id, submission.event_id)
    await validate_assets(db, author, submission.image_ids, "note_image", True)


async def publish_result(db, sub):
    job = await db.scalar(select(m.Job).where(m.Job.dedupe_key == "review_note:" + sub.id).with_for_update())
    return {
        "note_id": sub.note_id,
        "submission_id": sub.id,
        "review_status": sub.status,
        "job_id": job.id if job else None,
    }


@router.post("/notes/{id}/publish", status_code=202)
async def publish(
    id: str,
    body: s.PublishInput,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    operation = "publish_note:" + id
    record, h = await idempotency(db, user, operation, idempotency_key, body.model_dump())
    if record:
        return await publish_result(db, await get(db, m.NoteSubmission, record.resource_id, True))
    n = await own(db, id, user, True)
    if n.status == "hidden":
        fail(409, "content_hidden")
    d = await get(db, m.NoteDraft, id, True)
    version(d, body.expected_edit_version, "edit_version")
    sub = await db.scalar(
        select(m.NoteSubmission)
        .where(m.NoteSubmission.note_id == id, m.NoteSubmission.based_on_edit_version == d.edit_version)
        .with_for_update()
    )
    if not sub:
        await validate_submission(db, n, d)
        number = (
            await db.scalar(
                select(func.max(m.NoteSubmission.submission_no)).where(m.NoteSubmission.note_id == id)
            )
            or 0
        ) + 1
        sub = m.NoteSubmission(
            note_id=id,
            submission_no=number,
            based_on_edit_version=d.edit_version,
            **{k: getattr(d, k) for k in ["title", "body_text", "image_ids", "place_id", "event_id"]},
        )
        db.add(sub)
        await db.flush()
        await enqueue(db, "review_note", sub.id)
    await remember(db, user, operation, idempotency_key, h, sub.id, 202)
    return await publish_result(db, sub)


@router.get("/notes/{id}/publication", response_model=out.Publication)
async def publication(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    n = await own(db, id, user)
    sub = await latest_submission(db, id)
    return {
        "submission_id": sub.id if sub else None,
        "review_status": sub.status if sub else None,
        "is_current_published": bool(sub and n.status == "published" and n.published_submission_id == sub.id),
        "reason_code": sub.reason_code if sub else None,
    }


@router.delete("/notes/{id}", status_code=204)
async def remove(
    id: str, body: s.VersionInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    n = await own(db, id, user, True)
    version(n, body.expected_version)
    n.status = "deleted"
    n.deleted_at = now()
    n.version += 1
    await enqueue(db, "cleanup", id, {"type": "note"})


@router.get("/me/notes", response_model=out.Page[out.Note])
async def mine(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    rows, nxt = await basic_list(
        db,
        m.Note,
        limit,
        cursor,
        [m.Note.author_id == user.id, m.Note.status == "published"],
        "my_notes:" + user.id,
    )
    return page([await note_response(db, n, user) for n in rows], nxt)


@router.get("/me/note-drafts", response_model=out.Page[out.NoteDraft])
async def drafts(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    rows, nxt = await basic_list(
        db,
        m.Note,
        limit,
        cursor,
        [m.Note.author_id == user.id, m.Note.status != "deleted"],
        "my_drafts:" + user.id,
    )
    return page([await draft_response(db, n) for n in rows], nxt)


async def apply_submission(db, n, sub):
    await validate_submission(db, n, sub)
    for k in ["title", "body_text", "place_id", "event_id"]:
        setattr(n, k, getattr(sub, k))
    await db.execute(delete(m.NoteImage).where(m.NoteImage.note_id == n.id))
    for i, id in enumerate(sub.image_ids):
        db.add(m.NoteImage(note_id=n.id, asset_id=id, position=i))
    n.status = "published"
    n.published_submission_id = sub.id
    n.published_at = now()
    n.first_published_at = n.first_published_at or now()
    n.version += 1

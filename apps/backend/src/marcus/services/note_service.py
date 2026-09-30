"""用户笔记业务：执行规则检查、数据库操作及相关任务安排；事务由调用方管理。"""

from sqlalchemy import select

from marcus import models as m
from marcus import schemas as s
from marcus.core.common import city_exists, data, enqueue, fail, get, idempotency, page, remember, version
from marcus.core.security import now
from marcus.repositories import note_repository
from marcus.services.catalog_service import basic_list
from marcus.services.content_service import author_summary, links_response, note_links, reactions, visible
from marcus.services.media_service import media_response, validate_assets


async def own(db, id, user, lock=False):
    n = await get(db, m.Note, id, lock)
    if n.author_id != user.id or n.status == "deleted":
        fail(404, "not_found")
    return n


async def note_response(db, n, user):
    images = await note_repository.published_images(db, n.id)
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


async def draft_response(db, n):
    d = await get(db, m.NoteDraft, n.id)
    out = data(d)
    latest = await note_repository.latest_submission(db, n.id)
    out.update(
        version=n.version,
        latest_submission=(
            {**data(latest), "review_status": latest.status, "submission_id": latest.id} if latest else None
        ),
        media=[await media_response(db, await get(db, m.MediaAsset, id)) for id in d.image_ids],
    )
    return out


async def create(body: s.CreateContent, user, db, idempotency_key: str | None):
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


async def read(id: str, user, db):
    n = await get(db, m.Note, id)
    await visible(db, n, user)
    return await note_response(db, n, user)


async def draft(id: str, user, db):
    return await draft_response(db, await own(db, id, user))


async def save(id: str, body: s.NoteDraftInput, user, db):
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


async def publish(id: str, body: s.PublishInput, user, db, idempotency_key: str | None):
    operation = "publish_note:" + id
    record, h = await idempotency(db, user, operation, idempotency_key, body.model_dump())
    if record:
        return await publish_result(db, await get(db, m.NoteSubmission, record.resource_id, True))
    n = await own(db, id, user, True)
    if n.status == "hidden":
        fail(409, "content_hidden")
    d = await get(db, m.NoteDraft, id, True)
    version(d, body.expected_edit_version, "edit_version")
    sub = await note_repository.submission_for_edit_locked(db, id, d.edit_version)
    if not sub:
        await validate_submission(db, n, d)
        number = await note_repository.highest_submission_number(db, id) + 1
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


async def publication(id: str, user, db):
    n = await own(db, id, user)
    sub = await note_repository.latest_submission(db, id)
    return {
        "submission_id": sub.id if sub else None,
        "review_status": sub.status if sub else None,
        "is_current_published": bool(sub and n.status == "published" and n.published_submission_id == sub.id),
        "reason_code": sub.reason_code if sub else None,
    }


async def remove(id: str, body: s.VersionInput, user, db):
    n = await own(db, id, user, True)
    version(n, body.expected_version)
    n.status = "deleted"
    n.deleted_at = now()
    n.version += 1
    await enqueue(db, "cleanup", id, {"type": "note"})


async def mine(limit: int, cursor: str | None, user, db):
    rows, nxt = await basic_list(
        db,
        m.Note,
        limit,
        cursor,
        [m.Note.author_id == user.id, m.Note.status == "published"],
        "my_notes:" + user.id,
    )
    return page([await note_response(db, n, user) for n in rows], nxt)


async def drafts(limit: int, cursor: str | None, user, db):
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
    await note_repository.replace_published_images(db, n.id, sub.image_ids)
    n.status = "published"
    n.published_submission_id = sub.id
    n.published_at = now()
    n.first_published_at = n.first_published_at or now()
    n.version += 1

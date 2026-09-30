"""审核、下架、恢复和账号管理；调用者传入操作者与请求编号，不传 HTTP 请求对象。"""

from sqlalchemy import select, update

from marcus.catalog.service import basic_list
from marcus.contracts import schemas as s
from marcus.core.common import audit, data, fail, get, page, version
from marcus.core.security import now
from marcus.database import models as m
from marcus.editorials.service import apply_revision
from marcus.media.service import media_response
from marcus.notes.service import apply_submission


async def note_review_response(db, sub):
    result = data(sub)
    result["media"] = [await media_response(db, await get(db, m.MediaAsset, id)) for id in sub.image_ids]
    return result


async def editorial_review_response(db, review):
    r = await get(db, m.EditorRevision, review.revision_id)
    result = data(review)
    result["revision"] = data(r)
    assets = (
        await db.scalars(
            select(m.MediaAsset)
            .join(m.EditorRevisionAsset, m.EditorRevisionAsset.asset_id == m.MediaAsset.id)
            .where(m.EditorRevisionAsset.revision_id == r.id)
            .distinct()
        )
    ).all()
    result["media"] = [await media_response(db, a) for a in assets]
    return result


async def note_queue(limit: int, cursor: str | None, status: str, user, db):
    rows, nxt = await basic_list(
        db, m.NoteSubmission, limit, cursor, [m.NoteSubmission.status == status], "note_queue:" + status
    )
    return page([data(x) for x in rows], nxt)


async def note_review(id: str, user, db):
    return await note_review_response(db, await get(db, m.NoteSubmission, id))


async def article_queue(limit: int, cursor: str | None, status: str, user, db):
    rows, nxt = await basic_list(
        db, m.EditorReview, limit, cursor, [m.EditorReview.status == status], "article_queue:" + status
    )
    return page([await editorial_review_response(db, x) for x in rows], nxt)


async def article_review(id: str, user, db):
    return await editorial_review_response(db, await get(db, m.EditorReview, id))


async def decide_note(db, id, body, user, request_id: str | None = None):
    prior = await get(db, m.NoteSubmission, id)
    n = await get(db, m.Note, prior.note_id, True)
    sub = await get(db, m.NoteSubmission, id, True)
    version(sub, body.expected_review_version, "review_version")
    if sub.status != "pending":
        fail(409, "already_reviewed")
    latest = await db.scalar(
        select(m.NoteSubmission.id)
        .where(m.NoteSubmission.note_id == n.id)
        .order_by(m.NoteSubmission.submission_no.desc())
        .limit(1)
        .with_for_update()
    )
    if body.decision == "approve" and latest == id and n.status not in ("hidden", "deleted"):
        await apply_submission(db, n, sub)
    sub.status = "approved" if body.decision == "approve" else "rejected"
    sub.reviewer_id = user.id if user else None
    sub.reason_code = body.reason_code
    sub.reviewer_note = body.note
    sub.reviewed_at = now()
    sub.review_version += 1
    await audit(db, request_id, user, "review_note", "note", n.id, body.reason_code)
    return await note_review_response(db, sub)


async def note_decision(id: str, body: s.DecisionInput, request_id: str | None, user, db):
    return await decide_note(db, id, body, user, request_id)


async def article_decision(id: str, body: s.DecisionInput, request_id: str | None, user, db):
    prior = await get(db, m.EditorReview, id)
    r = await get(db, m.EditorRevision, prior.revision_id)
    a = await get(db, m.EditorArticle, r.article_id, True)
    review = await get(db, m.EditorReview, id, True)
    version(review, body.expected_review_version)
    if review.status != "pending":
        fail(409, "already_reviewed")
    latest = await db.scalar(
        select(m.EditorRevision.id)
        .where(m.EditorRevision.article_id == a.id)
        .order_by(m.EditorRevision.revision_no.desc())
        .limit(1)
        .with_for_update()
    )
    if body.decision == "approve" and latest == r.id and a.status not in ("hidden", "deleted"):
        await apply_revision(db, a, r)
    review.status = "approved" if body.decision == "approve" else "rejected"
    review.reviewer_id = user.id
    review.reason_code = body.reason_code
    review.reviewer_note = body.note
    review.reviewed_at = now()
    review.version += 1
    await audit(db, request_id, user, "review_editorial", "editor_article", a.id, body.reason_code)
    return await editorial_review_response(db, review)


async def hide_content(db, model, id, body, user, request_id: str | None):
    obj = await get(db, model, id, True)
    version(obj, body.expected_version)
    if obj.status == "deleted":
        fail(409, "content_deleted")
    obj.status = "hidden"
    obj.version += 1
    await audit(db, request_id, user, "hide", model.__tablename__, id, body.reason)
    return {"id": id, "status": obj.status, "version": obj.version}


async def hide_note(id: str, body: s.HideInput, request_id: str | None, user, db):
    return await hide_content(db, m.Note, id, body, user, request_id)


async def hide_article(id: str, body: s.HideInput, request_id: str | None, user, db):
    return await hide_content(db, m.EditorArticle, id, body, user, request_id)


async def restore_note(id: str, body: s.VersionInput, request_id: str | None, user, db):
    n = await get(db, m.Note, id, True)
    version(n, body.expected_version)
    if n.status != "hidden" or not n.published_submission_id:
        fail(409, "no_publication_to_restore")
    sub = await get(db, m.NoteSubmission, n.published_submission_id)
    if sub.status != "approved":
        fail(409, "not_approved")
    await apply_submission(db, n, sub)
    await audit(db, request_id, user, "restore", "note", id)
    return data(n)


async def restore_article(id: str, body: s.VersionInput, request_id: str | None, user, db):
    a = await get(db, m.EditorArticle, id, True)
    version(a, body.expected_version)
    if a.status != "hidden" or not a.published_revision_id:
        fail(409, "no_publication_to_restore")
    r = await get(db, m.EditorRevision, a.published_revision_id)
    review = await db.scalar(select(m.EditorReview).where(m.EditorReview.revision_id == r.id))
    if review.status != "approved":
        fail(409, "not_approved")
    await apply_revision(db, a, r)
    await audit(db, request_id, user, "restore", "editor_article", id)
    return data(a)


async def grant(id: str, role: str, request_id: str | None, user, db):
    if role not in ("editor", "moderator", "admin"):
        fail(422, "invalid_role")
    await get(db, m.User, id, True)
    row = await db.get(m.UserRole, (id, role))
    if not row:
        db.add(m.UserRole(user_id=id, role=role, granted_by=user.id))
    await audit(db, request_id, user, "grant_role", "user", id, role)
    return {"user_id": id, "role": role}


async def revoke(id: str, role: str, request_id: str | None, user, db):
    from sqlalchemy import delete

    await db.execute(delete(m.UserRole).where(m.UserRole.user_id == id, m.UserRole.role == role))
    await audit(db, request_id, user, "revoke_role", "user", id, role)


async def suspend(id: str, body: s.SuspendInput, request_id: str | None, user, db):
    u = await get(db, m.User, id, True)
    if u.status == "deleted":
        fail(409, "account_deleted")
    u.status = "suspended"
    await db.execute(update(m.AuthSession).where(m.AuthSession.user_id == id).values(revoked_at=now()))
    await audit(db, request_id, user, "suspend", "user", id, body.reason)
    return {"id": id, "status": u.status}


async def note_state(id: str, user, db):
    obj = await get(db, m.Note, id)
    return {k: getattr(obj, k) for k in ["id", "status", "version", "published_submission_id"]}


async def article_state(id: str, user, db):
    obj = await get(db, m.EditorArticle, id)
    return {k: getattr(obj, k) for k in ["id", "status", "version", "published_revision_id"]}

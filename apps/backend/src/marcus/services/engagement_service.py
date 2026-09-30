"""处理收藏、点赞、拉黑、参与和举报，在同一次调用的数据库事务中保存业务变化。"""

from datetime import datetime, timezone

from sqlalchemy import delete, select

from marcus import models as m
from marcus import schemas as s
from marcus.core.common import audit, data, decode_cursor, encode_cursor, fail, get, page
from marcus.core.errors import ServiceError
from marcus.core.security import now
from marcus.services.catalog_service import basic_list
from marcus.services.content_service import reactions, visible
from marcus.services.editorial_service import article_response
from marcus.services.moderation_service import editorial_review_response, note_review_response
from marcus.services.note_service import note_response


async def react(db, user, id, kind, article, add):
    if kind not in ("like", "bookmark"):
        fail(422, "invalid_reaction")
    model = m.EditorArticle if article else m.Note
    rel = m.EditorArticleReaction if article else m.NoteReaction
    field = "article_id" if article else "note_id"
    row = await get(db, model, id, True)
    await visible(db, row, user)
    existing = await db.get(rel, (user.id, id, kind))
    if add and not existing:
        db.add(rel(user_id=user.id, kind=kind, **{field: id}))
    if not add and existing:
        await db.delete(existing)
    await db.flush()
    return await reactions(db, id, user, article)


async def note_add(id: str, kind: str, user, db):
    return await react(db, user, id, kind, False, True)


async def note_remove(id: str, kind: str, user, db):
    return await react(db, user, id, kind, False, False)


async def article_add(id: str, kind: str, user, db):
    return await react(db, user, id, kind, True, True)


async def article_remove(id: str, kind: str, user, db):
    return await react(db, user, id, kind, True, False)


async def block(id: str, user, db):
    if id == user.id:
        fail(422, "cannot_block_self")
    await get(db, m.User, user.id, True)
    await get(db, m.User, id)
    if not await db.get(m.UserBlock, (user.id, id)):
        db.add(m.UserBlock(user_id=user.id, blocked_user_id=id))


async def unblock(id: str, user, db):
    await db.execute(
        delete(m.UserBlock).where(m.UserBlock.user_id == user.id, m.UserBlock.blocked_user_id == id)
    )


async def participate(id: str, body: s.ParticipationInput, user, db):
    await get(db, m.User, user.id, True)
    e = await get(db, m.Event, id)
    if e.status == "draft":
        fail(404, "not_found")
    if body.session_id and (await get(db, m.EventSession, body.session_id)).event_id != id:
        fail(422, "session_event_mismatch")
    attended = body.attended_at
    if body.state == "attended":
        if not attended or attended.tzinfo is None:
            fail(422, "attended_time_required")
        attended = attended.astimezone(timezone.utc).replace(tzinfo=None)
        if attended > now():
            fail(422, "attended_time_future")
    else:
        attended = None
    row = await db.scalar(
        select(m.EventParticipation).where(
            m.EventParticipation.user_id == user.id, m.EventParticipation.event_id == id
        )
    )
    if not row:
        row = m.EventParticipation(user_id=user.id, event_id=id)
        db.add(row)
    row.state = body.state
    row.session_id = body.session_id
    row.attended_at = attended
    await db.flush()
    return data(row)


async def unparticipate(id: str, user, db):
    await db.execute(
        delete(m.EventParticipation).where(
            m.EventParticipation.user_id == user.id, m.EventParticipation.event_id == id
        )
    )


async def bookmarks(limit: int, cursor: str | None, user, db):
    from sqlalchemy import literal, union_all

    q = union_all(
        select(
            m.NoteReaction.created_at.label("time"),
            m.NoteReaction.note_id.label("id"),
            literal("note").label("kind"),
        ).where(m.NoteReaction.user_id == user.id, m.NoteReaction.kind == "bookmark"),
        select(
            m.EditorArticleReaction.created_at.label("time"),
            m.EditorArticleReaction.article_id.label("id"),
            literal("editorial").label("kind"),
        ).where(m.EditorArticleReaction.user_id == user.id, m.EditorArticleReaction.kind == "bookmark"),
    ).subquery()
    scope = "bookmarks:" + user.id
    last = decode_cursor(cursor, scope)
    query = select(q)
    from sqlalchemy import tuple_

    if last:
        query = query.where(
            tuple_(q.c.time, q.c.id, q.c.kind)
            < tuple_(literal(datetime.fromisoformat(last[0])), literal(last[1]), literal(last[2]))
        )
    rows = (
        await db.execute(query.order_by(q.c.time.desc(), q.c.id.desc(), q.c.kind.desc()).limit(limit + 1))
    ).all()
    items = []
    for row in rows[:limit]:
        model = m.Note if row.kind == "note" else m.EditorArticle
        obj = await get(db, model, row.id)
        try:
            await visible(db, obj, user)
        except ServiceError:
            continue
        content = await (
            note_response(db, obj, user) if row.kind == "note" else article_response(db, obj, user)
        )
        items.append({"content_type": row.kind, "content": content})
    nxt = (
        encode_cursor(scope, [rows[limit - 1].time.isoformat(), rows[limit - 1].id, rows[limit - 1].kind])
        if len(rows) > limit
        else None
    )
    return page(items, nxt)


async def report_note(id: str, body: s.NoteReportInput, user, db):
    n = await get(db, m.Note, id)
    await visible(db, n, user)
    if n.published_submission_id != body.submission_id:
        fail(422, "report_version_not_visible")
    r = m.NoteReport(reporter_id=user.id, note_id=id, **body.model_dump())
    db.add(r)
    await db.flush()
    return data(r)


async def report_article(id: str, body: s.EditorialReportInput, user, db):
    a = await get(db, m.EditorArticle, id)
    await visible(db, a, user)
    if a.published_revision_id != body.revision_id:
        fail(422, "report_version_not_visible")
    r = m.EditorArticleReport(reporter_id=user.id, article_id=id, **body.model_dump())
    db.add(r)
    await db.flush()
    return data(r)


async def note_reports(status: str | None, limit: int, cursor: str | None, user, db):
    rows, nxt = await basic_list(
        db,
        m.NoteReport,
        limit,
        cursor,
        [m.NoteReport.status == status] if status else [],
        scope="note_reports:" + str(status),
    )
    return page([data(x) for x in rows], nxt)


async def article_reports(status: str | None, limit: int, cursor: str | None, user, db):
    rows, nxt = await basic_list(
        db,
        m.EditorArticleReport,
        limit,
        cursor,
        [m.EditorArticleReport.status == status] if status else [],
        scope="article_reports:" + str(status),
    )
    return page([data(x) for x in rows], nxt)


async def note_report(id: str, user, db):
    r = await get(db, m.NoteReport, id)
    return {
        **data(r),
        "submission": await note_review_response(db, await get(db, m.NoteSubmission, r.submission_id)),
    }


async def article_report(id: str, user, db):
    r = await get(db, m.EditorArticleReport, id)
    review = await db.scalar(select(m.EditorReview).where(m.EditorReview.revision_id == r.revision_id))
    return {**data(r), "review": await editorial_review_response(db, review)}


async def resolve(db, model, id, body, user, request_id: str | None):
    r = await get(db, model, id, True)
    r.status = body.status
    r.resolution_note = body.resolution_note
    r.resolved_by = user.id
    await audit(db, request_id, user, "resolve_report", model.__tablename__, id, body.resolution_note)
    return data(r)


async def resolve_note(id: str, body: s.ResolutionInput, request_id: str | None, user, db):
    return await resolve(db, m.NoteReport, id, body, user, request_id)


async def resolve_article(id: str, body: s.ResolutionInput, request_id: str | None, user, db):
    return await resolve(db, m.EditorArticleReport, id, body, user, request_id)

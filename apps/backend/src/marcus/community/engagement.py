from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete, select

from marcus.catalog.api import basic_list
from marcus.community.content_common import reactions, visible
from marcus.contracts import schemas as s
from marcus.core.common import (
    audit,
    current_user,
    data,
    decode_cursor,
    encode_cursor,
    fail,
    get,
    moderator,
    page,
)
from marcus.core.db import get_session
from marcus.core.security import now
from marcus.database import models as m
from marcus.editorials.api import article_response
from marcus.moderation.api import editorial_review_response, note_review_response
from marcus.notes.api import note_response

router = APIRouter(tags=["engagement"])


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


@router.put("/notes/{id}/reactions/{kind}")
async def note_add(id: str, kind: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await react(db, user, id, kind, False, True)


@router.delete("/notes/{id}/reactions/{kind}")
async def note_remove(
    id: str, kind: str, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await react(db, user, id, kind, False, False)


@router.put("/editorials/{id}/reactions/{kind}")
async def article_add(
    id: str, kind: str, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await react(db, user, id, kind, True, True)


@router.delete("/editorials/{id}/reactions/{kind}")
async def article_remove(
    id: str, kind: str, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await react(db, user, id, kind, True, False)


@router.put("/users/{id}/block", status_code=204)
async def block(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    if id == user.id:
        fail(422, "cannot_block_self")
    await get(db, m.User, user.id, True)
    await get(db, m.User, id)
    if not await db.get(m.UserBlock, (user.id, id)):
        db.add(m.UserBlock(user_id=user.id, blocked_user_id=id))


@router.delete("/users/{id}/block", status_code=204)
async def unblock(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    await db.execute(
        delete(m.UserBlock).where(m.UserBlock.user_id == user.id, m.UserBlock.blocked_user_id == id)
    )


@router.put("/events/{id}/participation")
async def participate(
    id: str, body: s.ParticipationInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
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


@router.delete("/events/{id}/participation", status_code=204)
async def unparticipate(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    await db.execute(
        delete(m.EventParticipation).where(
            m.EventParticipation.user_id == user.id, m.EventParticipation.event_id == id
        )
    )


@router.get("/me/bookmarks")
async def bookmarks(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    # A signed key identifies the joint chronological stream across two actual relation tables.
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
        except HTTPException:
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


@router.post("/notes/{id}/reports", status_code=201)
async def report_note(
    id: str, body: s.NoteReportInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    n = await get(db, m.Note, id)
    await visible(db, n, user)
    if n.published_submission_id != body.submission_id:
        fail(422, "report_version_not_visible")
    r = m.NoteReport(reporter_id=user.id, note_id=id, **body.model_dump())
    db.add(r)
    await db.flush()
    return data(r)


@router.post("/editorials/{id}/reports", status_code=201)
async def report_article(
    id: str,
    body: s.EditorialReportInput,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    a = await get(db, m.EditorArticle, id)
    await visible(db, a, user)
    if a.published_revision_id != body.revision_id:
        fail(422, "report_version_not_visible")
    r = m.EditorArticleReport(reporter_id=user.id, article_id=id, **body.model_dump())
    db.add(r)
    await db.flush()
    return data(r)


@router.get("/admin/note-reports")
async def note_reports(
    status: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    rows, nxt = await basic_list(
        db,
        m.NoteReport,
        limit,
        cursor,
        [m.NoteReport.status == status] if status else [],
        scope="note_reports:" + str(status),
    )
    return page([data(x) for x in rows], nxt)


@router.get("/admin/editorial-reports")
async def article_reports(
    status: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    rows, nxt = await basic_list(
        db,
        m.EditorArticleReport,
        limit,
        cursor,
        [m.EditorArticleReport.status == status] if status else [],
        scope="article_reports:" + str(status),
    )
    return page([data(x) for x in rows], nxt)


@router.get("/admin/note-reports/{id}")
async def note_report(id: str, user=Depends(moderator), db=Depends(get_session, scope="function")):
    r = await get(db, m.NoteReport, id)
    return {
        **data(r),
        "submission": await note_review_response(db, await get(db, m.NoteSubmission, r.submission_id)),
    }


@router.get("/admin/editorial-reports/{id}")
async def article_report(id: str, user=Depends(moderator), db=Depends(get_session, scope="function")):
    r = await get(db, m.EditorArticleReport, id)
    review = await db.scalar(select(m.EditorReview).where(m.EditorReview.revision_id == r.revision_id))
    return {**data(r), "review": await editorial_review_response(db, review)}


async def resolve(db, model, id, body, user, request):
    r = await get(db, model, id, True)
    r.status = body.status
    r.resolution_note = body.resolution_note
    r.resolved_by = user.id
    await audit(db, request, user, "resolve_report", model.__tablename__, id, body.resolution_note)
    return data(r)


@router.patch("/admin/note-reports/{id}")
async def resolve_note(
    id: str,
    body: s.ResolutionInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await resolve(db, m.NoteReport, id, body, user, request)


@router.patch("/admin/editorial-reports/{id}")
async def resolve_article(
    id: str,
    body: s.ResolutionInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await resolve(db, m.EditorArticleReport, id, body, user, request)

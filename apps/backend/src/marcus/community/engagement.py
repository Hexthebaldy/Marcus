"""互动接口：接收点赞、收藏、参与和举报请求，业务处理交给 engagement_service.py。"""

from fastapi import APIRouter, Depends, Query, Request

from marcus.community import engagement_service as service
from marcus.contracts import schemas as s
from marcus.core.db import get_session
from marcus.core.dependencies import current_user, moderator

router = APIRouter(tags=["engagement"])


@router.put("/notes/{id}/reactions/{kind}")
async def note_add(id: str, kind: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.note_add(id, kind, user, db)


@router.delete("/notes/{id}/reactions/{kind}")
async def note_remove(
    id: str, kind: str, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.note_remove(id, kind, user, db)


@router.put("/editorials/{id}/reactions/{kind}")
async def article_add(
    id: str, kind: str, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.article_add(id, kind, user, db)


@router.delete("/editorials/{id}/reactions/{kind}")
async def article_remove(
    id: str, kind: str, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.article_remove(id, kind, user, db)


@router.put("/users/{id}/block", status_code=204)
async def block(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.block(id, user, db)


@router.delete("/users/{id}/block", status_code=204)
async def unblock(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.unblock(id, user, db)


@router.put("/events/{id}/participation")
async def participate(
    id: str, body: s.ParticipationInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.participate(id, body, user, db)


@router.delete("/events/{id}/participation", status_code=204)
async def unparticipate(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.unparticipate(id, user, db)


@router.get("/me/bookmarks")
async def bookmarks(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.bookmarks(limit, cursor, user, db)


@router.post("/notes/{id}/reports", status_code=201)
async def report_note(
    id: str, body: s.NoteReportInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.report_note(id, body, user, db)


@router.post("/editorials/{id}/reports", status_code=201)
async def report_article(
    id: str,
    body: s.EditorialReportInput,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.report_article(id, body, user, db)


@router.get("/admin/note-reports")
async def note_reports(
    status: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.note_reports(status, limit, cursor, user, db)


@router.get("/admin/editorial-reports")
async def article_reports(
    status: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.article_reports(status, limit, cursor, user, db)


@router.get("/admin/note-reports/{id}")
async def note_report(id: str, user=Depends(moderator), db=Depends(get_session, scope="function")):
    return await service.note_report(id, user, db)


@router.get("/admin/editorial-reports/{id}")
async def article_report(id: str, user=Depends(moderator), db=Depends(get_session, scope="function")):
    return await service.article_report(id, user, db)


@router.patch("/admin/note-reports/{id}")
async def resolve_note(
    id: str,
    body: s.ResolutionInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.resolve_note(id, body, getattr(request.state, "request_id", None), user, db)


@router.patch("/admin/editorial-reports/{id}")
async def resolve_article(
    id: str,
    body: s.ResolutionInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.resolve_article(id, body, getattr(request.state, "request_id", None), user, db)

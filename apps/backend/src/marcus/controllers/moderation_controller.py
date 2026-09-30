"""审核管理接口：接收参数与操作者，业务处理交给同目录的 service.py。"""

from fastapi import APIRouter, Depends, Query, Request

from marcus import schemas as s
from marcus.controllers.dependencies import admin, moderator
from marcus.core.db import get_session
from marcus.services import moderation_service as service

router = APIRouter(tags=["moderation"])


@router.get("/admin/note-submissions")
async def note_queue(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    status: str = "pending",
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.note_queue(limit, cursor, status, user, db)


@router.get("/admin/note-submissions/{id}")
async def note_review(id: str, user=Depends(moderator), db=Depends(get_session, scope="function")):
    return await service.note_review(id, user, db)


@router.get("/admin/editorial-reviews")
async def article_queue(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    status: str = "pending",
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.article_queue(limit, cursor, status, user, db)


@router.get("/admin/editorial-reviews/{id}")
async def article_review(id: str, user=Depends(moderator), db=Depends(get_session, scope="function")):
    return await service.article_review(id, user, db)


@router.post("/admin/note-submissions/{id}/decision")
async def note_decision(
    id: str,
    body: s.DecisionInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.note_decision(id, body, getattr(request.state, "request_id", None), user, db)


@router.post("/admin/editorial-reviews/{id}/decision")
async def article_decision(
    id: str,
    body: s.DecisionInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.article_decision(id, body, getattr(request.state, "request_id", None), user, db)


@router.post("/admin/notes/{id}/hide")
async def hide_note(
    id: str,
    body: s.HideInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.hide_note(id, body, getattr(request.state, "request_id", None), user, db)


@router.post("/admin/editorials/{id}/hide")
async def hide_article(
    id: str,
    body: s.HideInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.hide_article(id, body, getattr(request.state, "request_id", None), user, db)


@router.post("/admin/notes/{id}/restore")
async def restore_note(
    id: str,
    body: s.VersionInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.restore_note(id, body, getattr(request.state, "request_id", None), user, db)


@router.post("/admin/editorials/{id}/restore")
async def restore_article(
    id: str,
    body: s.VersionInput,
    request: Request,
    user=Depends(moderator),
    db=Depends(get_session, scope="function"),
):
    return await service.restore_article(id, body, getattr(request.state, "request_id", None), user, db)


@router.put("/admin/users/{id}/roles/{role}")
async def grant(
    id: str, role: str, request: Request, user=Depends(admin), db=Depends(get_session, scope="function")
):
    return await service.grant(id, role, getattr(request.state, "request_id", None), user, db)


@router.delete("/admin/users/{id}/roles/{role}", status_code=204)
async def revoke(
    id: str, role: str, request: Request, user=Depends(admin), db=Depends(get_session, scope="function")
):
    return await service.revoke(id, role, getattr(request.state, "request_id", None), user, db)


@router.post("/admin/users/{id}/suspend")
async def suspend(
    id: str,
    body: s.SuspendInput,
    request: Request,
    user=Depends(admin),
    db=Depends(get_session, scope="function"),
):
    return await service.suspend(id, body, getattr(request.state, "request_id", None), user, db)


@router.get("/admin/notes/{id}")
async def note_state(id: str, user=Depends(moderator), db=Depends(get_session, scope="function")):
    return await service.note_state(id, user, db)


@router.get("/admin/editorials/{id}")
async def article_state(id: str, user=Depends(moderator), db=Depends(get_session, scope="function")):
    return await service.article_state(id, user, db)

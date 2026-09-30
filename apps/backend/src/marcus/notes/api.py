"""用户笔记接口：接收请求参数并检查登录权限，将具体操作交给 service。"""

from fastapi import APIRouter, Depends, Header, Query

from marcus.contracts import responses as out
from marcus.contracts import schemas as s
from marcus.core.db import get_session
from marcus.core.dependencies import current_user
from marcus.notes import service

router = APIRouter(tags=["notes"])


@router.post("/notes", status_code=201, response_model=out.NoteDraft)
async def create(
    body: s.CreateContent,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    return await service.create(body=body, user=user, db=db, idempotency_key=idempotency_key)


@router.get("/notes/{id}", response_model=out.Note)
async def read(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.read(id=id, user=user, db=db)


@router.get("/notes/{id}/draft", response_model=out.NoteDraft)
async def draft(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.draft(id=id, user=user, db=db)


@router.patch("/notes/{id}/draft", response_model=out.NoteDraft)
async def save(
    id: str, body: s.NoteDraftInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.save(id=id, body=body, user=user, db=db)


@router.post("/notes/{id}/publish", status_code=202)
async def publish(
    id: str,
    body: s.PublishInput,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    return await service.publish(id=id, body=body, user=user, db=db, idempotency_key=idempotency_key)


@router.get("/notes/{id}/publication", response_model=out.Publication)
async def publication(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.publication(id=id, user=user, db=db)


@router.delete("/notes/{id}", status_code=204)
async def remove(
    id: str, body: s.VersionInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.remove(id=id, body=body, user=user, db=db)


@router.get("/me/notes", response_model=out.Page[out.Note])
async def mine(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.mine(limit=limit, cursor=cursor, user=user, db=db)


@router.get("/me/note-drafts", response_model=out.Page[out.NoteDraft])
async def drafts(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.drafts(limit=limit, cursor=cursor, user=user, db=db)

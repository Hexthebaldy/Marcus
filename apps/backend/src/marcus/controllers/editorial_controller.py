"""编辑文章接口：接收请求参数并检查登录权限，将具体操作交给 service。"""

from fastapi import APIRouter, Depends, Header, Query, Request

from marcus import schemas as s
from marcus.controllers.dependencies import current_user, editor
from marcus.core.db import get_session
from marcus.schemas import responses as out
from marcus.services import editorial_service as service

router = APIRouter(tags=["editorials"])


@router.get("/editorials/{id}", response_model=out.Editorial)
async def read(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.read(id=id, user=user, db=db)


@router.get("/admin/editorials")
async def admin_list(
    city_id: str | None = None,
    district_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    return await service.admin_list(
        city_id=city_id, district_id=district_id, limit=limit, cursor=cursor, user=user, db=db
    )


@router.post("/admin/editorials", status_code=201)
async def create(
    body: s.CreateEditorial,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    return await service.create(body=body, user=user, db=db, idempotency_key=idempotency_key)


@router.get("/admin/editorials/{id}/draft")
async def draft(id: str, user=Depends(editor), db=Depends(get_session, scope="function")):
    return await service.draft(id=id, user=user, db=db)


@router.patch("/admin/editorials/{id}/draft")
async def save(
    id: str, body: s.EditorialDraftInput, user=Depends(editor), db=Depends(get_session, scope="function")
):
    return await service.save(id=id, body=body, user=user, db=db)


@router.post("/admin/editorials/{id}/publish", status_code=202)
async def publish(
    id: str,
    body: s.PublishInput,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    return await service.publish(id=id, body=body, user=user, db=db, idempotency_key=idempotency_key)


@router.get("/admin/editorials/{id}/publication")
async def publication(id: str, user=Depends(editor), db=Depends(get_session, scope="function")):
    return await service.publication(id=id, user=user, db=db)


@router.patch("/admin/editorials/{id}")
async def settings_update(
    id: str,
    body: s.ArticleSettingsInput,
    request: Request,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    return await service.settings_update(
        id=id, body=body, request_id=getattr(request.state, "request_id", None), user=user, db=db
    )

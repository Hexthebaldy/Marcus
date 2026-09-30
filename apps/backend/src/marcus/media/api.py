"""媒体上传和访问接口：接收请求参数并检查登录权限，将具体操作交给 service。"""

from fastapi import APIRouter, Depends, Header

from marcus.contracts import responses as out
from marcus.contracts import schemas as s
from marcus.core.db import get_session
from marcus.core.dependencies import current_user
from marcus.media import service

router = APIRouter(tags=["media"])


@router.post("/media/uploads", status_code=201)
async def upload(
    body: s.UploadInput,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
    idempotency_key: str | None = Header(None),
):
    return await service.upload(body=body, user=user, db=db, idempotency_key=idempotency_key)


@router.post("/media/{id}/complete", status_code=202)
async def complete(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.complete(id=id, user=user, db=db)


@router.get("/media/{id}", response_model=out.MediaAsset)
async def read(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.read(id=id, user=user, db=db)


@router.delete("/media/{id}", status_code=204)
async def remove(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.remove(id=id, user=user, db=db)

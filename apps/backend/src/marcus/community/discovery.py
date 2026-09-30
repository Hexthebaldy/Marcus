"""Discover 接口：接收城市、区域和分页参数，列表查询交给 discovery_service.py。"""

from fastapi import APIRouter, Depends, Query

from marcus.community import discovery_service as service
from marcus.contracts import responses as out
from marcus.core.db import get_session
from marcus.core.dependencies import current_user

router = APIRouter(tags=["discovery"])


@router.get("/discover/notes", response_model=out.Page[out.Note])
async def notes(
    city_id: str,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.notes(city_id, limit, cursor, user, db)


@router.get("/discover/editorials", response_model=out.Page[out.Editorial])
async def articles(
    city_id: str,
    district_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.articles(city_id, district_id, limit, cursor, user, db)

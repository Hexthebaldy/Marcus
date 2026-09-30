"""城市、地点、活动和标签接口：接收请求参数并检查登录权限，将具体操作交给 service。"""

from fastapi import APIRouter, Depends, Query, Request

from marcus import schemas as s
from marcus.controllers.dependencies import current_user, editor
from marcus.core.db import get_session
from marcus.schemas import responses as out
from marcus.services import catalog_service as service

router = APIRouter(tags=["catalog"])


@router.get("/cities", response_model=out.Page[out.City])
async def cities(user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.cities(user=user, db=db)


@router.get("/cities/{id}/districts", response_model=out.Page[out.District])
async def districts(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.districts(id=id, user=user, db=db)


@router.get("/tags", response_model=out.Page[out.Tag])
async def tags(user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.tags(user=user, db=db)


@router.get("/places", response_model=out.Page[out.Place])
async def places(
    city_id: str,
    q: str = "",
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.places(city_id=city_id, q=q, limit=limit, cursor=cursor, user=user, db=db)


@router.get("/events", response_model=out.Page[out.Event])
async def events(
    city_id: str,
    q: str = "",
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.events(city_id=city_id, q=q, limit=limit, cursor=cursor, user=user, db=db)


@router.get("/places/{id}", response_model=out.Place)
async def place(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.place(id=id, user=user, db=db)


@router.get("/events/{id}", response_model=out.Event)
async def event(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.event(id=id, user=user, db=db)


@router.get("/events/{id}/sessions", response_model=out.Page[out.EventSession])
async def sessions(
    id: str,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await service.sessions(id=id, limit=limit, cursor=cursor, user=user, db=db)


@router.get("/admin/places")
async def admin_places(
    city_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    return await service.admin_places(city_id=city_id, limit=limit, cursor=cursor, user=user, db=db)


@router.post("/admin/places", status_code=201)
async def create_place(
    body: s.PlaceInput, request: Request, user=Depends(editor), db=Depends(get_session, scope="function")
):
    return await service.create_place(
        body=body, request_id=getattr(request.state, "request_id", None), user=user, db=db
    )


@router.get("/admin/places/{id}")
async def admin_place(id: str, user=Depends(editor), db=Depends(get_session, scope="function")):
    return await service.admin_place(id=id, user=user, db=db)


@router.patch("/admin/places/{id}")
async def patch_place(
    id: str,
    body: s.PlacePatch,
    request: Request,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    return await service.patch_place(
        id=id, body=body, request_id=getattr(request.state, "request_id", None), user=user, db=db
    )


@router.put("/admin/places/{id}/images")
async def place_images(
    id: str, body: s.ImagesInput, user=Depends(editor), db=Depends(get_session, scope="function")
):
    return await service.place_images(id=id, body=body, user=user, db=db)


@router.get("/admin/events")
async def admin_events(
    city_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    return await service.admin_events(city_id=city_id, limit=limit, cursor=cursor, user=user, db=db)


@router.post("/admin/events", status_code=201)
async def create_event(
    body: s.EventInput, request: Request, user=Depends(editor), db=Depends(get_session, scope="function")
):
    return await service.create_event(
        body=body, request_id=getattr(request.state, "request_id", None), user=user, db=db
    )


@router.get("/admin/events/{id}")
async def admin_event(id: str, user=Depends(editor), db=Depends(get_session, scope="function")):
    return await service.admin_event(id=id, user=user, db=db)


@router.patch("/admin/events/{id}")
async def patch_event(
    id: str,
    body: s.EventPatch,
    request: Request,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    return await service.patch_event(
        id=id, body=body, request_id=getattr(request.state, "request_id", None), user=user, db=db
    )


@router.post("/admin/events/{id}/sessions", status_code=201)
async def create_session(
    id: str, body: s.SessionInput, user=Depends(editor), db=Depends(get_session, scope="function")
):
    return await service.create_session(id=id, body=body, user=user, db=db)


@router.patch("/admin/events/{id}/sessions/{session_id}")
async def patch_session(
    id: str,
    session_id: str,
    body: s.SessionPatch,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    return await service.patch_session(id=id, session_id=session_id, body=body, user=user, db=db)


@router.get("/admin/tags")
async def admin_tags(user=Depends(editor), db=Depends(get_session, scope="function")):
    return await service.admin_tags(user=user, db=db)


@router.post("/admin/tags", status_code=201)
async def create_tag(body: s.TagInput, user=Depends(editor), db=Depends(get_session, scope="function")):
    return await service.create_tag(body=body, user=user, db=db)


@router.patch("/admin/tags/{id}")
async def patch_tag(
    id: str, body: s.TagPatch, user=Depends(editor), db=Depends(get_session, scope="function")
):
    return await service.patch_tag(id=id, body=body, user=user, db=db)


@router.get("/admin/events/{id}/sessions")
async def admin_sessions(
    id: str,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    return await service.admin_sessions(id=id, limit=limit, cursor=cursor, user=user, db=db)

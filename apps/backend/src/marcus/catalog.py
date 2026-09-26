from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from . import models as m
from . import responses as out
from . import schemas as s
from .common import (
    audit,
    city_exists,
    current_user,
    data,
    decode_cursor,
    editor,
    encode_cursor,
    fail,
    get,
    page,
    version,
)
from .db import get_session
from .media import media_response, validate_assets
from .security import now

router = APIRouter(tags=["catalog"])


async def place_response(db, p):
    value = {
        k: getattr(p, k)
        for k in [
            "id",
            "name",
            "address",
            "summary",
            "opening_hours_text",
            "transport_notes",
            "status",
            "verified_at",
            "version",
        ]
    }
    value.update(
        city=data(await get(db, m.City, p.city_id)),
        district=data(await get(db, m.District, p.district_id)),
        coordinates={"latitude": float(p.latitude), "longitude": float(p.longitude)}
        if p.latitude is not None
        else None,
        cover=await media_response(db, await db.get(m.MediaAsset, p.cover_asset_id))
        if p.cover_asset_id
        else None,
    )
    assets = (
        await db.scalars(
            select(m.MediaAsset)
            .join(m.PlaceAsset, m.PlaceAsset.asset_id == m.MediaAsset.id)
            .where(m.PlaceAsset.place_id == p.id)
            .order_by(m.PlaceAsset.position)
        )
    ).all()
    value["gallery"] = [await media_response(db, a) for a in assets]
    return value


async def event_response(db, e):
    p = await db.get(m.Place, e.place_id) if e.place_id else None
    value = {
        k: getattr(e, k)
        for k in [
            "id",
            "title",
            "description",
            "organizer",
            "booking_url",
            "status",
            "verified_at",
            "version",
        ]
    }
    value.update(
        city=data(await get(db, m.City, e.city_id)),
        place=await place_response(db, p) if p and p.status != "draft" else None,
        price={
            "status": e.price_status,
            "min_fen": e.price_min_fen,
            "max_fen": e.price_max_fen,
            "currency": e.currency,
        },
    )
    value["upcoming_sessions"] = [
        data(x)
        for x in (
            await db.scalars(
                select(m.EventSession)
                .where(m.EventSession.event_id == e.id, m.EventSession.ends_at >= now())
                .order_by(m.EventSession.starts_at)
                .limit(5)
            )
        ).all()
    ]
    return value


async def basic_list(db, model, limit=50, cursor=None, filters=(), scope="list"):
    q = select(model).where(*filters)
    last = decode_cursor(cursor, scope)
    if last:
        q = q.where(model.id > last[0])
    rows = (await db.scalars(q.order_by(model.id).limit(limit + 1))).all()
    return rows[:limit], encode_cursor(scope, [rows[limit - 1].id]) if len(rows) > limit else None


@router.get("/cities", response_model=out.Page[out.City])
async def cities(user=Depends(current_user), db=Depends(get_session, scope="function")):
    return page([data(x) for x in (await db.scalars(select(m.City).where(m.City.enabled.is_(True)))).all()])


@router.get("/cities/{id}/districts", response_model=out.Page[out.District])
async def districts(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    await city_exists(db, id)
    return page(
        [
            data(x)
            for x in (
                await db.scalars(select(m.District).where(m.District.city_id == id).order_by(m.District.code))
            ).all()
        ]
    )


@router.get("/tags", response_model=out.Page[out.Tag])
async def tags(user=Depends(current_user), db=Depends(get_session, scope="function")):
    return page(
        [
            data(x)
            for x in (
                await db.scalars(select(m.Tag).where(m.Tag.enabled.is_(True)).order_by(m.Tag.name))
            ).all()
        ]
    )


@router.get("/places", response_model=out.Page[out.Place])
async def places(
    city_id: str,
    q: str = "",
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    rows, next_ = await basic_list(
        db,
        m.Place,
        limit,
        cursor,
        [
            m.Place.city_id == city_id,
            m.Place.status.in_(["active", "closed"]),
            m.Place.name.contains(q, autoescape=True),
        ],
        "places:" + city_id + ":" + q,
    )
    return page([await place_response(db, x) for x in rows], next_)


@router.get("/events", response_model=out.Page[out.Event])
async def events(
    city_id: str,
    q: str = "",
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    rows, next_ = await basic_list(
        db,
        m.Event,
        limit,
        cursor,
        [m.Event.city_id == city_id, m.Event.status != "draft", m.Event.title.contains(q, autoescape=True)],
        "events:" + city_id + ":" + q,
    )
    return page([await event_response(db, x) for x in rows], next_)


@router.get("/places/{id}", response_model=out.Place)
async def place(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    p = await get(db, m.Place, id)
    if p.status == "draft":
        fail(404, "not_found")
    return await place_response(db, p)


@router.get("/events/{id}", response_model=out.Event)
async def event(id: str, user=Depends(current_user), db=Depends(get_session, scope="function")):
    e = await get(db, m.Event, id)
    if e.status == "draft":
        fail(404, "not_found")
    return await event_response(db, e)


@router.get("/events/{id}/sessions", response_model=out.Page[out.EventSession])
async def sessions(
    id: str,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    e = await get(db, m.Event, id)
    if e.status == "draft":
        fail(404, "not_found")
    rows, nxt = await basic_list(
        db, m.EventSession, limit, cursor, [m.EventSession.event_id == id], "sessions:" + id
    )
    return page([data(x) for x in rows], nxt)


def url_check(value):
    if value and (urlsplit(value).scheme not in ("http", "https") or not urlsplit(value).netloc):
        fail(422, "invalid_url")


async def validate_place(db, row, user):
    await city_exists(db, row.city_id)
    d = await get(db, m.District, row.district_id)
    if d.city_id != row.city_id:
        fail(422, "district_city_mismatch")
    if (row.latitude is None) != (row.longitude is None):
        fail(422, "coordinates_pair_required")
    if row.status != "draft" and not row.address.strip():
        fail(422, "address_required")
    url_check(row.source_url)
    if row.cover_asset_id:
        await validate_assets(db, user, [row.cover_asset_id], "place_image", True)


async def validate_event(db, row):
    await city_exists(db, row.city_id)
    if row.place_id:
        p = await get(db, m.Place, row.place_id)
        if p.city_id != row.city_id:
            fail(422, "place_city_mismatch")
        if row.status != "draft" and p.status == "draft":
            fail(422, "place_not_public")
    url_check(row.source_url)
    url_check(row.booking_url)
    if row.price_status == "free":
        row.price_min_fen = row.price_max_fen = 0
    if row.price_status == "unknown":
        row.price_min_fen = row.price_max_fen = None
    if row.price_status == "known" and (
        row.price_min_fen is None or row.price_max_fen is None or row.price_min_fen > row.price_max_fen
    ):
        fail(422, "invalid_price")


async def sync_districts(db, event_id=None, place_id=None):
    query = select(m.EditorArticle, m.EditorRevision).join(
        m.EditorRevision, m.EditorArticle.published_revision_id == m.EditorRevision.id
    )
    if event_id:
        query = query.where(m.EditorRevision.primary_event_id == event_id)
    for article, rev in (await db.execute(query)).all():
        pid = rev.primary_place_id
        if rev.primary_event_id:
            pid = (await get(db, m.Event, rev.primary_event_id)).place_id
        if place_id and pid != place_id:
            continue
        article.district_id = (await get(db, m.Place, pid)).district_id if pid else None


@router.get("/admin/places")
async def admin_places(
    city_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    rows, nxt = await basic_list(
        db,
        m.Place,
        limit,
        cursor,
        [m.Place.city_id == city_id] if city_id else [],
        scope="admin_places:" + str(city_id),
    )
    return page([data(x) for x in rows], nxt)


@router.post("/admin/places", status_code=201)
async def create_place(
    body: s.PlaceInput, request: Request, user=Depends(editor), db=Depends(get_session, scope="function")
):
    row = m.Place(**body.model_dump(exclude={"confirm_verified"}))
    await validate_place(db, row, user)
    if body.confirm_verified:
        row.verified_at = now()
    db.add(row)
    await db.flush()
    await audit(db, request, user, "create_place", "place", row.id)
    return data(row)


@router.get("/admin/places/{id}")
async def admin_place(id: str, user=Depends(editor), db=Depends(get_session, scope="function")):
    row = await get(db, m.Place, id)
    return {**data(row), **await place_response(db, row)}


@router.patch("/admin/places/{id}")
async def patch_place(
    id: str,
    body: s.PlacePatch,
    request: Request,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    row = await get(db, m.Place, id, True)
    version(row, body.expected_version)
    for k, v in body.model_dump(exclude_unset=True, exclude={"expected_version", "confirm_verified"}).items():
        setattr(row, k, v)
    await validate_place(db, row, user)
    if body.confirm_verified:
        row.verified_at = now()
    row.version += 1
    await sync_districts(db, place_id=id)
    await audit(db, request, user, "update_place", "place", id)
    return data(row)


@router.put("/admin/places/{id}/images")
async def place_images(
    id: str, body: s.ImagesInput, user=Depends(editor), db=Depends(get_session, scope="function")
):
    from sqlalchemy import delete

    row = await get(db, m.Place, id, True)
    version(row, body.expected_version)
    if len(set(body.asset_ids)) != len(body.asset_ids):
        fail(422, "duplicate_asset")
    await validate_assets(db, user, body.asset_ids, "place_image", True)
    await db.execute(delete(m.PlaceAsset).where(m.PlaceAsset.place_id == id))
    for i, a in enumerate(body.asset_ids):
        db.add(m.PlaceAsset(place_id=id, asset_id=a, position=i))
    row.version += 1
    return {"version": row.version, "asset_ids": body.asset_ids}


@router.get("/admin/events")
async def admin_events(
    city_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    rows, nxt = await basic_list(
        db,
        m.Event,
        limit,
        cursor,
        [m.Event.city_id == city_id] if city_id else [],
        scope="admin_events:" + str(city_id),
    )
    return page([data(x) for x in rows], nxt)


@router.post("/admin/events", status_code=201)
async def create_event(
    body: s.EventInput, request: Request, user=Depends(editor), db=Depends(get_session, scope="function")
):
    row = m.Event(**body.model_dump(exclude={"confirm_verified"}))
    await validate_event(db, row)
    if body.confirm_verified:
        row.verified_at = now()
    db.add(row)
    await db.flush()
    await audit(db, request, user, "create_event", "event", row.id)
    return data(row)


@router.get("/admin/events/{id}")
async def admin_event(id: str, user=Depends(editor), db=Depends(get_session, scope="function")):
    return data(await get(db, m.Event, id))


@router.patch("/admin/events/{id}")
async def patch_event(
    id: str,
    body: s.EventPatch,
    request: Request,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    row = await get(db, m.Event, id, True)
    version(row, body.expected_version)
    for k, v in body.model_dump(exclude_unset=True, exclude={"expected_version", "confirm_verified"}).items():
        setattr(row, k, v)
    await validate_event(db, row)
    if body.confirm_verified:
        row.verified_at = now()
    row.version += 1
    await sync_districts(db, event_id=id)
    await audit(db, request, user, "update_event", "event", id)
    return data(row)


@router.post("/admin/events/{id}/sessions", status_code=201)
async def create_session(
    id: str, body: s.SessionInput, user=Depends(editor), db=Depends(get_session, scope="function")
):
    await get(db, m.Event, id)
    row = m.EventSession(event_id=id, **body.model_dump())
    db.add(row)
    await db.flush()
    return data(row)


@router.patch("/admin/events/{id}/sessions/{session_id}")
async def patch_session(
    id: str,
    session_id: str,
    body: s.SessionPatch,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    row = await get(db, m.EventSession, session_id, True)
    if row.event_id != id:
        fail(404, "not_found")
    version(row, body.expected_version)
    for k, v in body.model_dump(exclude={"expected_version"}).items():
        setattr(row, k, v)
    row.version += 1
    return data(row)


@router.get("/admin/tags")
async def admin_tags(user=Depends(editor), db=Depends(get_session, scope="function")):
    return page([data(x) for x in (await db.scalars(select(m.Tag))).all()])


@router.post("/admin/tags", status_code=201)
async def create_tag(body: s.TagInput, user=Depends(editor), db=Depends(get_session, scope="function")):
    row = m.Tag(**body.model_dump())
    db.add(row)
    await db.flush()
    return data(row)


@router.patch("/admin/tags/{id}")
async def patch_tag(
    id: str, body: s.TagPatch, user=Depends(editor), db=Depends(get_session, scope="function")
):
    row = await get(db, m.Tag, id, True)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    return data(row)


@router.get("/admin/events/{id}/sessions")
async def admin_sessions(
    id: str,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(editor),
    db=Depends(get_session, scope="function"),
):
    await get(db, m.Event, id)
    rows, nxt = await basic_list(
        db, m.EventSession, limit, cursor, [m.EventSession.event_id == id], "admin_sessions:" + id
    )
    return page([data(x) for x in rows], nxt)

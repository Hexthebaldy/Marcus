from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, tuple_

from marcus.contracts import responses as out
from marcus.core.common import city_exists, current_user, decode_cursor, encode_cursor, fail, get, page
from marcus.core.db import get_session
from marcus.database import models as m
from marcus.editorials.api import article_response
from marcus.notes.api import note_response

router = APIRouter(tags=["discovery"])


async def feed(db, user, city_id, limit, cursor, editorial=False, district_id=None):
    await city_exists(db, city_id)
    if district_id and (await get(db, m.District, district_id)).city_id != city_id:
        fail(422, "district_city_mismatch")
    model = m.EditorArticle if editorial else m.Note
    scope = f"feed:{editorial}:{city_id}:{district_id}:{user.id}"
    q = (
        select(model)
        .join(m.User, m.User.id == model.author_id)
        .where(
            model.city_id == city_id,
            model.status == "published",
            m.User.status == "active",
            ~model.author_id.in_(select(m.UserBlock.blocked_user_id).where(m.UserBlock.user_id == user.id)),
        )
    )
    last = decode_cursor(cursor, scope)
    if editorial:
        if district_id:
            q = q.where(model.district_id == district_id)
        if last:
            q = q.where(
                tuple_(model.editorial_rank, model.first_published_at, model.id)
                < tuple_(int(last[0]), datetime.fromisoformat(last[1]), last[2])
            )
        q = q.order_by(model.editorial_rank.desc(), model.first_published_at.desc(), model.id.desc())
    else:
        if last:
            q = q.where(
                tuple_(model.first_published_at, model.id) < tuple_(datetime.fromisoformat(last[0]), last[1])
            )
        q = q.order_by(model.first_published_at.desc(), model.id.desc())
    rows = (await db.scalars(q.limit(limit + 1))).all()
    nxt = None
    if len(rows) > limit:
        row = rows[limit - 1]
        values = [row.first_published_at.isoformat(), row.id]
        if editorial:
            values.insert(0, row.editorial_rank)
        nxt = encode_cursor(scope, values)
    return page(
        [
            await (article_response(db, row, user) if editorial else note_response(db, row, user))
            for row in rows[:limit]
        ],
        nxt,
    )


@router.get("/discover/notes", response_model=out.Page[out.Note])
async def notes(
    city_id: str,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await feed(db, user, city_id, limit, cursor)


@router.get("/discover/editorials", response_model=out.Page[out.Editorial])
async def articles(
    city_id: str,
    district_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    return await feed(db, user, city_id, limit, cursor, True, district_id)

"""查询 Discover 内容、过滤不可见内容，并生成下一页位置。"""

from datetime import datetime

from sqlalchemy import literal, select, tuple_

from marcus.core.common import city_exists, decode_cursor, encode_cursor, fail, get, page
from marcus.database import models as m
from marcus.editorials.service import article_response
from marcus.notes.service import note_response


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
            q = q.where(m.EditorArticle.district_id == district_id)
        if last:
            q = q.where(
                tuple_(m.EditorArticle.editorial_rank, model.first_published_at, model.id)
                < tuple_(literal(int(last[0])), literal(datetime.fromisoformat(last[1])), literal(last[2]))
            )
        q = q.order_by(
            m.EditorArticle.editorial_rank.desc(), model.first_published_at.desc(), model.id.desc()
        )
    else:
        if last:
            q = q.where(
                tuple_(model.first_published_at, model.id)
                < tuple_(literal(datetime.fromisoformat(last[0])), literal(last[1]))
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


async def notes(city_id: str, limit: int, cursor: str | None, user, db):
    return await feed(db, user, city_id, limit, cursor)


async def articles(city_id: str, district_id: str | None, limit: int, cursor: str | None, user, db):
    return await feed(db, user, city_id, limit, cursor, True, district_id)

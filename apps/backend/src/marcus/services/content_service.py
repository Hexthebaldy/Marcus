from sqlalchemy import func, select

from marcus import models as m
from marcus.core.common import fail, get
from marcus.services.catalog_service import event_response, place_response
from marcus.services.media_service import media_response


async def author_summary(db, id):
    u = await get(db, m.User, id)
    return {
        "id": u.id,
        "display_name": u.display_name,
        "avatar": await media_response(db, await db.get(m.MediaAsset, u.avatar_asset_id))
        if u.avatar_asset_id
        else None,
    }


async def visible(db, row, user):
    if row.status != "published" or (await get(db, m.User, row.author_id)).status != "active":
        fail(404, "not_found")
    if await db.get(m.UserBlock, (user.id, row.author_id)):
        fail(404, "not_found")


async def reactions(db, id, user, editorial=False):
    model = m.EditorArticleReaction if editorial else m.NoteReaction
    col = m.EditorArticleReaction.article_id if editorial else m.NoteReaction.note_id
    counts = dict(
        (await db.execute(select(model.kind, func.count()).where(col == id).group_by(model.kind))).all()
    )
    own = set((await db.scalars(select(model.kind).where(col == id, model.user_id == user.id))).all())
    return {
        "like_count": counts.get("like", 0),
        "bookmark_count": counts.get("bookmark", 0),
        "liked": "like" in own,
        "bookmarked": "bookmark" in own,
    }


async def note_links(db, city_id, place_id, event_id):
    if event_id:
        e = await get(db, m.Event, event_id)
        if e.status == "draft" or e.city_id != city_id:
            fail(422, "event_not_public_or_wrong_city")
        if place_id and place_id != e.place_id:
            fail(422, "event_place_mismatch")
        place_id = e.place_id
    if place_id:
        p = await get(db, m.Place, place_id)
        if p.status == "draft" or p.city_id != city_id:
            fail(422, "place_not_public_or_wrong_city")
    return place_id


async def links_response(db, place_id, event_id):
    e = await db.get(m.Event, event_id) if event_id else None
    # Historical submissions stay immutable; the visit card follows the current event venue.
    current_place_id = e.place_id if e else place_id
    p = await db.get(m.Place, current_place_id) if current_place_id else None
    return {
        "place": await place_response(db, p) if p and p.status != "draft" else None,
        "event": await event_response(db, e) if e and e.status != "draft" else None,
    }

"""查询城市、区域、标签、地点图片和活动场次，维护图库关联；这里不提交事务。"""

from sqlalchemy import delete, select

from marcus import models as m
from marcus.core.security import now


async def place_assets(db, place_id):
    """联查 place_assets 与 media_assets，按图库位置返回地点图片。"""
    return (
        await db.scalars(
            select(m.MediaAsset)
            .join(m.PlaceAsset, m.PlaceAsset.asset_id == m.MediaAsset.id)
            .where(m.PlaceAsset.place_id == place_id)
            .order_by(m.PlaceAsset.position)
        )
    ).all()


async def upcoming_sessions(db, event_id):
    """从 event_sessions 查询尚未结束的场次，按开始时间取前五条。"""
    return (
        await db.scalars(
            select(m.EventSession)
            .where(m.EventSession.event_id == event_id, m.EventSession.ends_at >= now())
            .order_by(m.EventSession.starts_at)
            .limit(5)
        )
    ).all()


async def enabled_cities(db):
    """查询 cities 表中 enabled 为真的城市。"""
    return (await db.scalars(select(m.City).where(m.City.enabled.is_(True)))).all()


async def city_districts(db, city_id):
    """查询 districts 表中属于指定城市的区，按行政区代码排序。"""
    return (
        await db.scalars(select(m.District).where(m.District.city_id == city_id).order_by(m.District.code))
    ).all()


async def enabled_tags(db):
    """查询 tags 表中启用的标签，按名称排序。"""
    return (await db.scalars(select(m.Tag).where(m.Tag.enabled.is_(True)).order_by(m.Tag.name))).all()


async def all_tags(db):
    """查询 tags 表的全部标签，包括后台管理需要显示的停用标签。"""
    return (await db.scalars(select(m.Tag))).all()


async def published_article_revisions(db, event_id=None):
    """联查文章和当前公开版本；传入活动编号时只返回主推该活动的文章。"""
    query = select(m.EditorArticle, m.EditorRevision).join(
        m.EditorRevision, m.EditorArticle.published_revision_id == m.EditorRevision.id
    )
    if event_id:
        query = query.where(m.EditorRevision.primary_event_id == event_id)
    return (await db.execute(query)).all()


async def replace_place_images(db, place_id, asset_ids):
    """删除 place_assets 旧关联，再按传入顺序登记新的图库图片关联。"""
    await db.execute(delete(m.PlaceAsset).where(m.PlaceAsset.place_id == place_id))
    for i, a in enumerate(asset_ids):
        db.add(m.PlaceAsset(place_id=place_id, asset_id=a, position=i))

"""查询编辑文章的版本、审核和素材关联，并登记版本关联；这里不提交事务。"""

from sqlalchemy import func, select

from marcus import models as m


async def latest_revision(db, article_id):
    """从 editor_revisions 取该文章版本序号最大的一条，未提交时返回 None。"""
    return await db.scalar(
        select(m.EditorRevision)
        .where(m.EditorRevision.article_id == article_id)
        .order_by(m.EditorRevision.revision_no.desc())
        .limit(1)
    )


async def revision_tags(db, revision_id):
    """联查 editor_revision_tags 与 tags，返回这个文章版本的标签。"""
    return (
        await db.scalars(
            select(m.Tag)
            .join(m.EditorRevisionTag, m.EditorRevisionTag.tag_id == m.Tag.id)
            .where(m.EditorRevisionTag.revision_id == revision_id)
        )
    ).all()


async def revision_assets(db, revision_id):
    """联查 editor_revision_assets 与 media_assets，返回该版本去重后的素材。"""
    return (
        await db.scalars(
            select(m.MediaAsset)
            .join(m.EditorRevisionAsset, m.EditorRevisionAsset.asset_id == m.MediaAsset.id)
            .where(m.EditorRevisionAsset.revision_id == revision_id)
            .distinct()
        )
    ).all()


async def revision_for_edit_locked(db, article_id, edit_version):
    """锁住文章同一个草稿版本的提交记录，供发布流程检查是否已经提交。"""
    return await db.scalar(
        select(m.EditorRevision)
        .where(
            m.EditorRevision.article_id == article_id, m.EditorRevision.based_on_edit_version == edit_version
        )
        .with_for_update()
    )


async def highest_revision_number(db, article_id):
    """查询该文章已经使用的最大版本序号，没有版本时返回 0。"""
    return (
        await db.scalar(
            select(func.max(m.EditorRevision.revision_no)).where(m.EditorRevision.article_id == article_id)
        )
        or 0
    )


async def review_for_revision_locked(db, revision_id):
    """按文章版本查询 editor_reviews 并锁住审核行，未找到时返回 None。"""
    return await db.scalar(
        select(m.EditorReview).where(m.EditorReview.revision_id == revision_id).with_for_update()
    )


def add_revision_links(db, revision_id, tag_ids, media_ids, cover_asset_id):
    """把版本标签、正文素材和封面关联加入待写入对象；调用方随后 flush。"""
    for tid in tag_ids:
        db.add(m.EditorRevisionTag(revision_id=revision_id, tag_id=tid))
    for aid in media_ids:
        db.add(m.EditorRevisionAsset(revision_id=revision_id, asset_id=aid, role="inline"))
    if cover_asset_id:
        db.add(m.EditorRevisionAsset(revision_id=revision_id, asset_id=cover_asset_id, role="cover"))

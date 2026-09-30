"""查询笔记图片和投稿版本，替换已发布图片关联；这里不提交事务。"""

from sqlalchemy import delete, func, select

from marcus import models as m


async def published_images(db, note_id):
    """联查 note_images 与 media_assets，按笔记中的图片位置返回素材。"""
    return (
        await db.scalars(
            select(m.MediaAsset)
            .join(m.NoteImage, m.NoteImage.asset_id == m.MediaAsset.id)
            .where(m.NoteImage.note_id == note_id)
            .order_by(m.NoteImage.position)
        )
    ).all()


async def latest_submission(db, note_id):
    """从 note_submissions 取投稿序号最大的一条，未投稿时返回 None。"""
    return await db.scalar(
        select(m.NoteSubmission)
        .where(m.NoteSubmission.note_id == note_id)
        .order_by(m.NoteSubmission.submission_no.desc())
        .limit(1)
    )


async def submission_for_edit_locked(db, note_id, edit_version):
    """锁住该笔记、该草稿版本对应的投稿，避免重复提交相同版本。"""
    return await db.scalar(
        select(m.NoteSubmission)
        .where(m.NoteSubmission.note_id == note_id, m.NoteSubmission.based_on_edit_version == edit_version)
        .with_for_update()
    )


async def highest_submission_number(db, note_id):
    """查询该笔记已经使用的最大投稿序号，没有投稿时返回 0。"""
    return (
        await db.scalar(
            select(func.max(m.NoteSubmission.submission_no)).where(m.NoteSubmission.note_id == note_id)
        )
        or 0
    )


async def replace_published_images(db, note_id, image_ids):
    """删除 note_images 旧关联，再按传入顺序登记这次发布的图片关联。"""
    await db.execute(delete(m.NoteImage).where(m.NoteImage.note_id == note_id))
    for i, id in enumerate(image_ids):
        db.add(m.NoteImage(note_id=note_id, asset_id=id, position=i))

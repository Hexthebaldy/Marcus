"""查询验证码、用户和续期凭证，写入发送限额及批量撤销记录；这里不提交事务。"""

from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert

from marcus import models as m
from marcus.core.security import now


async def ensure_send_limit_locked(db, lookup, purpose):
    """先确保 auth_send_limits 中有邮箱与用途对应的行，再锁住并返回这行。"""
    stmt = insert(m.AuthSendLimit).values(
        email_lookup_hash=lookup,
        purpose=purpose,
        next_allowed_at=now(),
        created_at=now(),
        updated_at=now(),
    )
    await db.execute(stmt.on_duplicate_key_update(email_lookup_hash=lookup))
    return await db.scalar(
        select(m.AuthSendLimit)
        .where(m.AuthSendLimit.email_lookup_hash == lookup, m.AuthSendLimit.purpose == purpose)
        .with_for_update()
    )


async def expire_open_challenges(db, lookup, purpose):
    """使这个邮箱及用途尚未消耗的验证码失效，并清除待发送验证码密文。"""
    await db.execute(
        update(m.AuthChallenge)
        .where(
            m.AuthChallenge.email_lookup_hash == lookup,
            m.AuthChallenge.purpose == purpose,
            m.AuthChallenge.consumed_at.is_(None),
        )
        .values(expires_at=now(), delivery_code_ciphertext=None)
    )


async def lock_login_gate(db, lookup):
    """锁住 auth_send_limits 的登录行，让同一邮箱的并发验证按顺序执行。"""
    await db.scalar(
        select(m.AuthSendLimit)
        .where(
            m.AuthSendLimit.email_lookup_hash == lookup,
            m.AuthSendLimit.purpose == "login",
        )
        .with_for_update()
    )


async def user_by_email(db, lookup):
    """从 users 表按邮箱摘要查用户，未找到时返回 None。"""
    return await db.scalar(select(m.User).where(m.User.email_lookup_hash == lookup))


async def refresh_token_locked(db, token_hash):
    """按摘要查询 refresh_tokens 并锁住匹配行，防止同一凭证被同时消耗。"""
    return await db.scalar(
        select(m.RefreshToken).where(m.RefreshToken.token_hash == token_hash).with_for_update()
    )


async def revoke_sessions_and_delete_content(db, user_id):
    """撤销用户所有 auth_sessions，并把其 notes 与 editor_articles 批量标记为删除。"""
    await db.execute(update(m.AuthSession).where(m.AuthSession.user_id == user_id).values(revoked_at=now()))
    for model in (m.Note, m.EditorArticle):
        await db.execute(
            update(model).where(model.author_id == user_id).values(status="deleted", deleted_at=now())
        )

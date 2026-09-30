"""生成验证码、管理登录与用户资料；邮件和任务写入由调用者的数据库事务统一保存。"""

import hmac
import secrets
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from marcus import models as m
from marcus import schemas as s
from marcus.core.common import city_exists, data, enqueue, fail, get, roles
from marcus.core.config import settings
from marcus.core.security import access_token, digest, encrypt, new_refresh, normalize_email, now
from marcus.repositories import auth_repository


@dataclass
class IssuedTokens:
    """签发结果；接口层决定把续期凭证写入 Cookie 还是响应正文。"""

    result: dict[str, Any]
    refresh_token: str
    client_type: str


async def profile(db, user):
    from marcus.services.media_service import media_response

    return {
        "id": user.id,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar": await media_response(db, await db.get(m.MediaAsset, user.avatar_asset_id))
        if user.avatar_asset_id
        else None,
        "city": data(await db.get(m.City, user.city_id)) if user.city_id else None,
        "roles": sorted(await roles(db, user.id)),
    }


async def rate_limit(client_ip: str):
    if not settings.rate_limit_enabled:
        return
    r = Redis.from_url(settings.redis_url)
    try:
        key = "auth-ip:" + digest(client_ip)
        # Redis shares eval typing with its synchronous client; this async script returns INCR's integer.
        count = await cast(
            Awaitable[int],
            r.eval(
                "local n=redis.call('INCR',KEYS[1]);if n==1 then redis.call('EXPIRE',KEYS[1],600) end;return n",
                1,
                key,
            ),
        )
    except RedisError:
        fail(503, "rate_limiter_unavailable")
    finally:
        await r.aclose()
    if count > 20:
        fail(429, "too_many_requests")


async def challenge(db, body: s.ChallengeInput, user=None):
    email = normalize_email(str(body.email))
    lookup = digest("email:" + email)
    if body.purpose == "delete_account":
        if user is None:
            fail(401, "authentication_required")
        if user.email_lookup_hash != lookup:
            fail(403, "email_mismatch")
    limit = await auth_repository.ensure_send_limit_locked(db, lookup, body.purpose)
    if limit.next_allowed_at > now():
        fail(429, "resend_too_soon")
    limit.next_allowed_at = now() + timedelta(seconds=60)
    await auth_repository.expire_open_challenges(db, lookup, body.purpose)
    id = str(uuid4())
    code = f"{secrets.randbelow(1000000):06d}"
    c = m.AuthChallenge(
        id=id,
        email_lookup_hash=lookup,
        email_ciphertext=encrypt(email),
        purpose=body.purpose,
        code_hmac=digest(f"{lookup}:{id}:{code}"),
        delivery_code_ciphertext=encrypt(code),
        expires_at=now() + timedelta(minutes=5),
        terms_version=body.terms_version,
    )
    db.add(c)
    await db.flush()
    await enqueue(db, "send_verification_email", id)
    return {"challenge_id": id, "expires_in_seconds": 300, "resend_after_seconds": 60}


async def consume(db, id, code, purpose):
    """验证并消耗一次验证码；错误次数需先提交，避免错误响应回滚后丢失计数。"""
    c = await get(db, m.AuthChallenge, id, True)
    if c.purpose != purpose or c.consumed_at or c.expires_at <= now() or c.attempts >= c.max_attempts:
        fail(422, "invalid_challenge")
    c.attempts += 1
    if not hmac.compare_digest(c.code_hmac, digest(f"{c.email_lookup_hash}:{c.id}:{code}")):
        await db.commit()  # failed attempts must survive the error response
        fail(422, "invalid_code")
    c.consumed_at = now()
    c.delivery_code_ciphertext = None
    return c


async def issue(db, user, session, parent=None):
    """保存续期凭证摘要，返回访问凭证与续期原文，HTTP 层负责选择传输位置。"""
    token = new_refresh()
    row = m.RefreshToken(
        session_id=session.id,
        token_hash=digest(token),
        parent_id=parent.id if parent else None,
        expires_at=min(now() + timedelta(days=7), session.absolute_expires_at),
    )
    db.add(row)
    result = {
        "access_token": access_token(user.id, session.id),
        "expires_in": 900,
        "session_id": session.id,
        "user": await profile(db, user),
    }
    return IssuedTokens(result=result, refresh_token=token, client_type=session.client_type)


async def verify(db, body: s.VerifyInput):
    # Lookup gate serializes verification and concurrent first registration of one email.
    original = await get(db, m.AuthChallenge, body.challenge_id)
    await auth_repository.lock_login_gate(db, original.email_lookup_hash)
    c = await consume(db, body.challenge_id, body.code, "login")
    user = await auth_repository.user_by_email(db, c.email_lookup_hash)
    if not user:
        user = m.User(
            email_lookup_hash=c.email_lookup_hash,
            email_ciphertext=c.email_ciphertext,
            email_verified_at=now(),
            display_name="城市漫游者",
            bio="",
            terms_version=c.terms_version,
            terms_accepted_at=now(),
        )
        db.add(user)
        await db.flush()
    if user.status != "active":
        fail(403, "account_inactive")
    session = m.AuthSession(
        user_id=user.id,
        client_type=body.client_type,
        device_label=body.device_label,
        last_seen_at=now(),
        absolute_expires_at=now() + timedelta(days=30),
    )
    db.add(session)
    await db.flush()
    return await issue(db, user, session)


async def refresh_context(db, token: str | None):
    """锁住续期凭证和登录记录，供接口先检查 Web 来源，再执行续期。"""
    if not token:
        fail(401, "refresh_required")
    old = await auth_repository.refresh_token_locked(db, digest(token))
    if not old:
        fail(401, "invalid_refresh")
    session = await get(db, m.AuthSession, old.session_id, True)
    return old, session


async def refresh(db, old, session):
    """消费已锁住的旧凭证并签发新凭证；发现重用时先提交撤销结果，再报告失败。"""
    user = await get(db, m.User, session.user_id)
    if old.used_at:
        session.revoked_at = now()
        await db.commit()
        fail(401, "refresh_reused")
    if (
        old.revoked_at
        or old.expires_at <= now()
        or session.revoked_at
        or session.absolute_expires_at <= now()
        or user.status != "active"
    ):
        fail(401, "session_inactive")
    old.used_at = now()
    session.last_seen_at = now()
    return await issue(db, user, session, old)


async def logout(db, session):
    session.revoked_at = now()


async def me(db, user):
    return await profile(db, user)


async def edit_me(db, user, body: s.ProfileInput):
    values = body.model_dump(exclude_unset=True)
    if values.get("city_id"):
        await city_exists(db, values["city_id"])
    if values.get("avatar_asset_id"):
        from marcus.services.media_service import validate_assets

        await validate_assets(db, user, [values["avatar_asset_id"]], "avatar", ready=True)
    for k, v in values.items():
        setattr(user, k, v)
    await db.flush()
    return await profile(db, user)


async def delete_me(db, user, body: s.DeleteAccountInput):
    c = await consume(db, body.challenge_id, body.code, "delete_account")
    if c.email_lookup_hash != user.email_lookup_hash:
        fail(403, "email_mismatch")
    await auth_repository.revoke_sessions_and_delete_content(db, user.id)
    user.status = "deleted"
    user.deleted_at = now()
    user.email_ciphertext = None
    user.email_lookup_hash = None
    user.email_verified_at = None
    user.display_name = "已注销用户"
    user.bio = ""
    user.avatar_asset_id = None
    await enqueue(db, "cleanup", user.id, {"type": "user"})

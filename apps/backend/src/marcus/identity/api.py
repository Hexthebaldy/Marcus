import hmac
import secrets
from collections.abc import Awaitable
from datetime import timedelta
from typing import cast
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert

from marcus.contracts import responses as out
from marcus.contracts import schemas as s
from marcus.core.common import check_origin, city_exists, current_user, data, enqueue, fail, get, roles
from marcus.core.config import settings
from marcus.core.db import get_session
from marcus.core.security import access_token, digest, encrypt, new_refresh, normalize_email, now
from marcus.database import models as m

router = APIRouter(tags=["identity"])


async def profile(db, user):
    from marcus.media.api import media_response

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


async def rate_limit(request):
    if not settings.rate_limit_enabled:
        return
    r = Redis.from_url(settings.redis_url)
    try:
        key = "auth-ip:" + digest(request.client.host if request.client else "unknown")
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


@router.post("/auth/challenges", status_code=201, response_model=out.Challenge)
async def challenge(body: s.ChallengeInput, request: Request, db=Depends(get_session, scope="function")):
    await rate_limit(request)
    email = normalize_email(str(body.email))
    lookup = digest("email:" + email)
    if body.purpose == "delete_account":
        user = await current_user(request, db)
        if user.email_lookup_hash != lookup:
            fail(403, "email_mismatch")
    stmt = insert(m.AuthSendLimit).values(
        email_lookup_hash=lookup,
        purpose=body.purpose,
        next_allowed_at=now(),
        created_at=now(),
        updated_at=now(),
    )
    await db.execute(stmt.on_duplicate_key_update(email_lookup_hash=lookup))
    limit = await db.scalar(
        select(m.AuthSendLimit)
        .where(m.AuthSendLimit.email_lookup_hash == lookup, m.AuthSendLimit.purpose == body.purpose)
        .with_for_update()
    )
    if limit.next_allowed_at > now():
        fail(429, "resend_too_soon")
    limit.next_allowed_at = now() + timedelta(seconds=60)
    await db.execute(
        update(m.AuthChallenge)
        .where(
            m.AuthChallenge.email_lookup_hash == lookup,
            m.AuthChallenge.purpose == body.purpose,
            m.AuthChallenge.consumed_at.is_(None),
        )
        .values(expires_at=now(), delivery_code_ciphertext=None)
    )
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


async def issue(db, user, session, response, parent=None):
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
    if session.client_type == "editor_web":
        response.set_cookie(
            "marcus_refresh",
            token,
            httponly=True,
            secure=settings.environment == "production",
            samesite="strict",
            path="/v1/auth",
            max_age=7 * 86400,
        )
    else:
        result["refresh_token"] = token
    return result


@router.post("/auth/verify", response_model=out.AuthResult, response_model_exclude_none=True)
async def verify(
    body: s.VerifyInput, request: Request, response: Response, db=Depends(get_session, scope="function")
):
    if body.client_type == "editor_web":
        check_origin(request)
    # Lookup gate serializes verification and concurrent first registration of one email.
    original = await get(db, m.AuthChallenge, body.challenge_id)
    await db.scalar(
        select(m.AuthSendLimit)
        .where(
            m.AuthSendLimit.email_lookup_hash == original.email_lookup_hash,
            m.AuthSendLimit.purpose == "login",
        )
        .with_for_update()
    )
    c = await consume(db, body.challenge_id, body.code, "login")
    user = await db.scalar(select(m.User).where(m.User.email_lookup_hash == c.email_lookup_hash))
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
    return await issue(db, user, session, response)


@router.post("/auth/refresh", response_model=out.AuthResult, response_model_exclude_none=True)
async def refresh(
    body: s.RefreshInput, request: Request, response: Response, db=Depends(get_session, scope="function")
):
    token = body.refresh_token or request.cookies.get("marcus_refresh")
    if not token:
        fail(401, "refresh_required")
    old = await db.scalar(
        select(m.RefreshToken).where(m.RefreshToken.token_hash == digest(token)).with_for_update()
    )
    if not old:
        fail(401, "invalid_refresh")
    session = await get(db, m.AuthSession, old.session_id, True)
    if session.client_type == "editor_web":
        check_origin(request)
        if body.refresh_token:
            fail(422, "web_refresh_uses_cookie")
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
    return await issue(db, user, session, response, old)


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    request.state.auth_session.revoked_at = now()
    response.delete_cookie("marcus_refresh", path="/v1/auth")


@router.get("/me", response_model=out.User)
async def me(user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await profile(db, user)


@router.patch("/me", response_model=out.User)
async def edit_me(
    body: s.ProfileInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    values = body.model_dump(exclude_unset=True)
    if values.get("city_id"):
        await city_exists(db, values["city_id"])
    if values.get("avatar_asset_id"):
        from marcus.media.api import validate_assets

        await validate_assets(db, user, [values["avatar_asset_id"]], "avatar", ready=True)
    for k, v in values.items():
        setattr(user, k, v)
    await db.flush()
    return await profile(db, user)


@router.delete("/me", status_code=204)
async def delete_me(
    body: s.DeleteAccountInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    c = await consume(db, body.challenge_id, body.code, "delete_account")
    if c.email_lookup_hash != user.email_lookup_hash:
        fail(403, "email_mismatch")
    await db.execute(update(m.AuthSession).where(m.AuthSession.user_id == user.id).values(revoked_at=now()))
    for model in (m.Note, m.EditorArticle):
        await db.execute(
            update(model).where(model.author_id == user.id).values(status="deleted", deleted_at=now())
        )
    user.status = "deleted"
    user.deleted_at = now()
    user.email_ciphertext = None
    user.email_lookup_hash = None
    user.email_verified_at = None
    user.display_name = "已注销用户"
    user.bio = ""
    user.avatar_asset_id = None
    await enqueue(db, "cleanup", user.id, {"type": "user"})

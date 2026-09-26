import base64
import hashlib
import hmac
import json
from datetime import timedelta
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marcus.core.config import settings
from marcus.core.db import get_session
from marcus.core.security import decode_token, digest, now
from marcus.database import models as m


def fail(status, code, message=None):
    raise HTTPException(status, detail={"code": code, "message": message or code, "details": {}})


def data(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def version(row, expected, field="version"):
    if getattr(row, field) != expected:
        fail(409, "version_conflict")


async def get(db, model, id, lock=False):
    query = select(model).where(model.__mapper__.primary_key[0] == id)
    if lock:
        query = query.with_for_update()
    row = await db.scalar(query.execution_options(populate_existing=True))
    if not row:
        fail(404, "not_found")
    return row


async def roles(db, user_id):
    return set((await db.scalars(select(m.UserRole.role).where(m.UserRole.user_id == user_id))).all())


def check_origin(request):
    if request.headers.get("origin") not in settings.origins:
        fail(403, "untrusted_origin")


async def current_user(request: Request, db: AsyncSession = Depends(get_session, scope="function")):
    token = request.headers.get("authorization", "")
    if not token.startswith("Bearer "):
        fail(401, "login_required")
    try:
        claims = decode_token(token[7:])
    except InvalidTokenError:
        fail(401, "invalid_access_token")
    session = await db.get(m.AuthSession, claims["sid"])
    user = await db.get(m.User, claims["sub"])
    if (
        not session
        or not user
        or session.user_id != user.id
        or session.revoked_at
        or session.absolute_expires_at <= now()
        or user.status != "active"
    ):
        fail(401, "session_inactive")
    if session.client_type == "editor_web" and request.method not in ("GET", "HEAD", "OPTIONS"):
        check_origin(request)
    request.state.auth_session = session
    return user


async def editor(user=Depends(current_user), db=Depends(get_session, scope="function")):
    if not await roles(db, user.id) & {"editor", "admin"}:
        fail(403, "editor_required")
    return user


async def moderator(user=Depends(current_user), db=Depends(get_session, scope="function")):
    if not await roles(db, user.id) & {"moderator", "admin"}:
        fail(403, "moderator_required")
    return user


async def admin(user=Depends(current_user), db=Depends(get_session, scope="function")):
    if "admin" not in await roles(db, user.id):
        fail(403, "admin_required")
    return user


async def city_exists(db, id):
    c = await get(db, m.City, id)
    if not c.enabled:
        fail(422, "city_unavailable")
    return c


async def audit(db, request, user, action, target_type, target_id, reason=None):
    db.add(
        m.AuditLog(
            actor_type="user" if user else "system",
            actor_id=user.id if user else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            request_id=getattr(request.state, "request_id", str(uuid4())) if request else str(uuid4()),
            reason=reason,
        )
    )


async def enqueue(db, kind, target_id, payload=None):
    key = f"{kind}:{target_id}"
    prior = await db.scalar(select(m.Job).where(m.Job.dedupe_key == key))
    if prior:
        return prior
    job = m.Job(kind=kind, target_id=target_id, dedupe_key=key, payload=payload or {}, available_at=now())
    db.add(job)
    await db.flush()
    return job


async def idempotency(db, user, operation, key, body):
    if not key or len(key) > 100:
        fail(422, "idempotency_key_required")
    # Lock a stable user row before checking/inserting to serialize concurrent first requests.
    await get(db, m.User, user.id, True)
    fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    record = await db.scalar(
        select(m.IdempotencyRecord)
        .where(
            m.IdempotencyRecord.user_id == user.id,
            m.IdempotencyRecord.operation == operation,
            m.IdempotencyRecord.request_key == key,
        )
        .with_for_update()
    )
    if record and record.request_hash != fingerprint:
        fail(409, "idempotency_payload_conflict")
    return record, fingerprint


async def remember(db, user, operation, key, fingerprint, id, status):
    db.add(
        m.IdempotencyRecord(
            user_id=user.id,
            operation=operation,
            request_key=key,
            request_hash=fingerprint,
            resource_id=id,
            response_status=status,
            expires_at=now() + timedelta(days=1),
        )
    )


def encode_cursor(scope, values):
    raw = base64.urlsafe_b64encode(
        json.dumps({"scope": scope, "values": values}, default=str, separators=(",", ":")).encode()
    ).decode()
    return raw + "." + digest(raw)


def decode_cursor(value, scope):
    if not value:
        return None
    try:
        raw, signature = value.rsplit(".", 1)
        if not hmac.compare_digest(signature, digest(raw)):
            raise ValueError()
        obj = json.loads(base64.urlsafe_b64decode(raw))
        if obj["scope"] != scope:
            raise ValueError()
        return obj["values"]
    except Exception:
        fail(422, "invalid_cursor")


def page(items, next_cursor=None):
    return {"items": items, "next_cursor": next_cursor}

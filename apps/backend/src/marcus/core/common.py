import base64
import hashlib
import hmac
import json
from datetime import timedelta
from typing import NoReturn
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marcus.core.config import settings
from marcus.core.db import get_session
from marcus.core.security import decode_token, digest, now
from marcus.database import models as m


def fail(status: int, code: str, message: str | None = None) -> NoReturn:
    """中断当前操作，抛出带统一错误内容的请求异常。
    """
    raise HTTPException(status, detail={"code": code, "message": message or code, "details": {}})


def data(row):
    """把数据库记录对象 row 的全部表字段转换为字典，不修改字段值或提交事务。
    """
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def version(row, expected, field="version"):
    """检查记录 row 的版本是否等于调用者提供的 expected，防止覆盖别人的修改。

    field 指定版本属性名，默认是 version。不一致时抛出 409 错误；一致时不修改记录。
    """
    if getattr(row, field) != expected:
        fail(409, "version_conflict")


async def get(db, model, id, lock=False):
    """通过数据库操作对象 db 查询 model 表，返回首个主键字段等于 id 的记录。

    找不到记录时抛出 404 错误。lock=True 时申请行锁，锁随当前事务结束而释放。
    这里仅使用第一个主键字段，不适合作为联合主键记录的完整查找方式。
    """
    query = select(model).where(model.__mapper__.primary_key[0] == id)
    if lock:
        query = query.with_for_update()
    # 即使 db 已加载过这个对象，也用本次查询结果更新它的属性。
    row = await db.scalar(query.execution_options(populate_existing=True))
    if not row:
        fail(404, "not_found")
    return row


async def roles(db, user_id):
    """通过 db 查询指定用户的角色，返回角色名称集合；没有角色时返回空集合。"""
    return set((await db.scalars(select(m.UserRole.role).where(m.UserRole.user_id == user_id))).all())


def check_origin(request):
    """检查请求的 Origin 来源是否在配置的允许列表中，否则抛出 403 错误。

    来源缺失也不会通过检查；允许列表来自 settings.origins。
    """
    if request.headers.get("origin") not in settings.origins:
        fail(403, "untrusted_origin")


async def current_user(request: Request, db: AsyncSession = Depends(get_session, scope="function")):
    """验证本次请求的登录凭证，返回仍可正常使用的用户记录。

    FastAPI 在需要登录的接口执行前调用本函数，并提供请求 request 和数据库操作对象 db。
    缺少凭证、凭证无效、登录记录失效或用户不可用时抛出 401 错误。
    编辑后台的修改请求还必须通过来源检查，否则抛出 403 错误。
    """
    token = request.headers.get("authorization", "")
    if not token.startswith("Bearer "):
        fail(401, "login_required")
    try:
        claims = decode_token(token[7:])
    except InvalidTokenError:
        fail(401, "invalid_access_token")
    # db 是执行查询的对象；session 是数据库中保存的一条用户登录记录，两者用途不同。
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
    # 把已验证的登录记录留在本次请求上，供后续接口代码使用。
    request.state.auth_session = session
    return user


async def editor(user=Depends(current_user), db=Depends(get_session, scope="function")):
    """要求当前用户具有编辑或管理员角色，成功时返回用户，否则抛出 403 错误。

    FastAPI 先调用 current_user 验证登录，再把用户和数据库操作对象交给本函数。
    """
    if not await roles(db, user.id) & {"editor", "admin"}:
        fail(403, "editor_required")
    return user


async def moderator(user=Depends(current_user), db=Depends(get_session, scope="function")):
    """要求当前用户具有审核或管理员角色，成功时返回用户，否则抛出 403 错误。

    FastAPI 先验证登录，再提供 user 和用于查询角色的数据库操作对象 db。
    """
    if not await roles(db, user.id) & {"moderator", "admin"}:
        fail(403, "moderator_required")
    return user


async def admin(user=Depends(current_user), db=Depends(get_session, scope="function")):
    """要求当前用户具有管理员角色，成功时返回用户，否则抛出 403 错误。

    FastAPI 先验证登录，再提供 user 和用于查询角色的数据库操作对象 db。
    """
    if "admin" not in await roles(db, user.id):
        fail(403, "admin_required")
    return user


async def city_exists(db, id):
    """通过 db 查询并返回已启用的城市；不存在时报 404，未启用时报 422。"""
    c = await get(db, m.City, id)
    if not c.enabled:
        fail(422, "city_unavailable")
    return c


async def audit(db, request, user, action, target_type, target_id, reason=None):
    """把一条操作记录加入 db，记下谁对什么对象做了什么，以及可选的原因。

    action 表示操作，target_type 和 target_id 表示目标；user 为空时记为系统操作。
    request 用于取得请求编号，没有请求或编号时生成新编号。本函数不提交事务。
    """
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
    """查找或创建针对 target_id 的后台任务，返回任务记录。

    kind 表示任务种类，payload 是任务所需的附加数据。同种类、同目标已有任务时直接返回它。
    新任务先写入当前事务，但本函数不提交；后台工作进程之后才会执行已提交的任务。
    """
    key = f"{kind}:{target_id}"
    prior = await db.scalar(select(m.Job).where(m.Job.dedupe_key == key))
    if prior:
        return prior
    job = m.Job(kind=kind, target_id=target_id, dedupe_key=key, payload=payload or {}, available_at=now())
    db.add(job)
    # flush 把新增记录发送给数据库并取得生成的字段值，不等于 commit 最终提交。
    await db.flush()
    return job


async def idempotency(db, user, operation, key, body):
    """检查一次操作是否已经处理过，避免用户重试时重复创建或发布。

    user、operation 和 key 共同标识这次操作；body 用于计算请求内容的摘要。
    返回已有记录（没有则为 None）和本次摘要。key 缺失或过长时报 422；
    同一个标识对应不同内容时报 409。本函数不创建结果记录，调用者随后用 remember 保存。
    """
    if not key or len(key) > 100:
        fail(422, "idempotency_key_required")
    # 先锁住用户行，让同一用户的并发请求依次检查，避免同时认为结果记录不存在。
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
    """把已处理操作的结果加入 db，供后续相同请求查找，不在这里提交事务。

    user、operation、key 标识操作，fingerprint 是请求摘要；id 是结果资源编号，
    status 是响应状态码。记录的到期时间设为一天后，过期记录由清理任务移除。
    """
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
    """把分页位置 values 和适用范围 scope 编成字符串，并附上防篡改签名。

    返回值供客户端请求下一页时传回。这里是编码和签名，不是加密，内容仍可被读取。
    """
    raw = base64.urlsafe_b64encode(
        json.dumps({"scope": scope, "values": values}, default=str, separators=(",", ":")).encode()
    ).decode()
    return raw + "." + digest(raw)


def decode_cursor(value, scope):
    """校验客户端传回的分页字符串，成功时返回其中的位置数据。

    value 为空时返回 None，表示没有指定分页位置。格式损坏、签名不符，
    或字符串中的适用范围与 scope 不同时，抛出 422 错误。
    """
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
    """把当前页内容 items 和下一页位置 next_cursor 组成统一的返回字典。

    next_cursor 默认为 None，表示没有下一页；本函数不查询数据或计算分页位置。
    """
    return {"items": items, "next_cursor": next_cursor}

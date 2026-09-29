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
    """检查记录 row 的版本是否等于调用者提供的 expected。
    """
    if getattr(row, field) != expected:
        fail(409, "version_conflict")


async def get(db, model, id, lock=False):
    """通过数据库操作对象 db 查询 model 表，返回首个主键字段等于 id 的记录。
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
    """用户获取验证码、完成图片上传或提交笔记时，把后续工作记入任务表。

    邮件发送、图片处理和笔记自动检查由后台工作进程执行，当前请求不必等待这些工作完成。
    kind 指定做什么，target_id 指定处理哪条验证码、媒体或笔记提交记录；
    payload 存放附加信息，例如清理任务要删除哪类内容。
    通过数据库操作对象 db 查找任务；同种类、同目标已有任务时返回原任务，否则创建并返回新任务。
    本函数不发送邮件、不处理图片，也不提交事务；任务提交后才可供后台工作进程领取。
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
    """用户创建或发布笔记后没收到响应、客户端重试时，检查是否已经处理过这次请求。

    客户端重试必须沿用同一个 key；本函数不会把用户所有创建或发布操作自动合并。
    user 指当前用户，operation 区分创建笔记、发布某篇笔记等操作，body 是本次请求内容。
    本函数通过 db 查找相同用户、操作和 key 的记录，并计算用于比较请求内容的摘要。
    返回已有记录（没有则为 None）和摘要；接口据此复用原笔记或原提交，或继续首次处理。
    key 缺失或过长时报 422，同一个 key 被用于不同内容时报 409。
    首次处理的结果由接口随后调用 remember 记录，本函数不创建结果记录。
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
    """接口首次创建笔记或生成发布提交后，记住它的编号，避免客户端重试时再创建一份。

    user、operation、key 标识刚处理的请求，fingerprint 是 idempotency 算出的请求内容摘要。
    id 是已创建的笔记、发布提交等资源编号，status 是这次响应的状态码。
    这里只记录资源编号等信息，不保存整份响应；重试时接口会读取原资源，再组装响应。
    记录通过 db 加入当前事务，本函数不提交。到期时间设为一天后，过期记录由清理任务移除。
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
    """用户浏览 Discover 并继续加载时，把这一页的结束位置做成客户端可以带回的字符串。

    例如 Notes 列表把本页最后一篇笔记的首次发布时间和编号放进 values，
    再用 scope 标明这是哪个用户、城市和内容列表的位置；Editor 列表还会带上编辑排序值。
    返回的字符串供客户端请求下一页时传回，接口据此从这个位置继续查询。
    本函数只编码这些信息并添加防篡改签名，不查询笔记，也不加密内容。
    """
    raw = base64.urlsafe_b64encode(
        json.dumps({"scope": scope, "values": values}, default=str, separators=(",", ":")).encode()
    ).decode()
    return raw + "." + digest(raw)


def decode_cursor(value, scope):
    """用户请求 Discover 下一页时，核对带回的分页位置字符串，并取出上次读到的位置。

    value 是客户端传回的字符串，scope 是接口根据当前用户、城市等条件确定的列表范围。
    成功时返回位置数据，例如 Notes 的发布时间和笔记编号；接口再用这些值查询下一批笔记。
    value 为空时返回 None，供接口从第一页开始。内容被改动、格式损坏或范围不符时报 422。
    本函数只校验和读取分页位置，不查询数据库，也不返回文章或笔记本身。
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
    """让 Discover 等列表接口用相同格式告诉客户端：这一页有哪些内容，还能否继续加载。

    items 是接口已经查好并整理好的内容，next_cursor 是接口准备的下一页位置字符串。
    返回包含这两个字段的字典；next_cursor 为 None 时表示没有下一页。
    本函数只组装返回格式，不查询数据库、不挑选内容，也不计算下一页的位置。
    """
    return {"items": items, "next_cursor": next_cursor}

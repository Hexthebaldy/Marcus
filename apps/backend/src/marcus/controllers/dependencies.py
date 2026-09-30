"""FastAPI 调用这些函数取得当前用户；请求头和请求临时状态只在接口层处理。"""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from marcus.core.common import fail
from marcus.core.config import settings
from marcus.core.db import get_session
from marcus.services.authentication_service import authenticate, require_roles


def check_origin(request: Request) -> None:
    """编辑后台提交修改或续期时，只接受配置中允许的网站来源。"""
    if request.headers.get("origin") not in settings.origins:
        fail(403, "untrusted_origin")


async def current_user(request: Request, db: AsyncSession = Depends(get_session, scope="function")):
    """取出请求头中的凭证，调用验证函数，把登录记录留给本次请求的退出接口。"""
    user, session = await authenticate(db, request.headers.get("authorization", ""))
    if session.client_type == "editor_web" and request.method not in ("GET", "HEAD", "OPTIONS"):
        check_origin(request)
    request.state.auth_session = session
    return user


async def editor(user=Depends(current_user), db=Depends(get_session, scope="function")):
    """接口执行前，要求已登录用户具备编辑或管理员角色。"""
    return await require_roles(db, user, {"editor", "admin"}, "editor_required")


async def moderator(user=Depends(current_user), db=Depends(get_session, scope="function")):
    """接口执行前，要求已登录用户具备审核或管理员角色。"""
    return await require_roles(db, user, {"moderator", "admin"}, "moderator_required")


async def admin(user=Depends(current_user), db=Depends(get_session, scope="function")):
    """接口执行前，要求已登录用户具备管理员角色。"""
    return await require_roles(db, user, {"admin"}, "admin_required")

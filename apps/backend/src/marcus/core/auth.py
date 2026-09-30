"""检查凭证、登录记录和角色；不读取 HTTP 请求，不构造 HTTP 响应。"""

from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from marcus.core.common import fail, roles
from marcus.core.security import decode_token, now
from marcus.database import models as m


async def authenticate(db: AsyncSession, authorization: str) -> tuple[m.User, m.AuthSession]:
    """验证传入的凭证文字，并返回有效的用户与登录记录。"""
    if not authorization.startswith("Bearer "):
        fail(401, "login_required")
    try:
        claims = decode_token(authorization[7:])
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
    return user, session


async def require_roles(db: AsyncSession, user: m.User, allowed: set[str], code: str) -> m.User:
    """查询用户角色，至少具备 allowed 中的一种才返回用户，否则报告失败。"""
    if not await roles(db, user.id) & allowed:
        fail(403, code)
    return user

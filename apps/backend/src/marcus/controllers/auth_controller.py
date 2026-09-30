"""邮箱登录与资料接口：读取 HTTP 参数、调用业务函数，并写回 Cookie 和响应。"""

from fastapi import APIRouter, Depends, Request, Response

from marcus import schemas as s
from marcus.controllers.dependencies import check_origin, current_user
from marcus.core.common import fail
from marcus.core.config import settings
from marcus.core.db import get_session
from marcus.schemas import responses as out
from marcus.services import auth_service as service

router = APIRouter(tags=["identity"])


def token_response(issued: service.IssuedTokens, response: Response):
    """编辑后台使用 HttpOnly Cookie，手机端从响应正文取得续期凭证。"""
    result = issued.result.copy()
    if issued.client_type == "editor_web":
        response.set_cookie(
            "marcus_refresh",
            issued.refresh_token,
            httponly=True,
            secure=settings.environment == "production",
            samesite="strict",
            path="/v1/auth",
            max_age=7 * 86400,
        )
    else:
        result["refresh_token"] = issued.refresh_token
    return result


@router.post("/auth/challenges", status_code=201, response_model=out.Challenge)
async def challenge(body: s.ChallengeInput, request: Request, db=Depends(get_session, scope="function")):
    await service.rate_limit(request.client.host if request.client else "unknown")
    user = await current_user(request, db) if body.purpose == "delete_account" else None
    return await service.challenge(db, body, user)


@router.post("/auth/verify", response_model=out.AuthResult, response_model_exclude_none=True)
async def verify(
    body: s.VerifyInput, request: Request, response: Response, db=Depends(get_session, scope="function")
):
    if body.client_type == "editor_web":
        check_origin(request)
    return token_response(await service.verify(db, body), response)


@router.post("/auth/refresh", response_model=out.AuthResult, response_model_exclude_none=True)
async def refresh(
    body: s.RefreshInput, request: Request, response: Response, db=Depends(get_session, scope="function")
):
    old, session = await service.refresh_context(
        db, body.refresh_token or request.cookies.get("marcus_refresh")
    )
    if session.client_type == "editor_web":
        check_origin(request)
        if body.refresh_token:
            fail(422, "web_refresh_uses_cookie")
    return token_response(await service.refresh(db, old, session), response)


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    user=Depends(current_user),
    db=Depends(get_session, scope="function"),
):
    await service.logout(db, request.state.auth_session)
    response.delete_cookie("marcus_refresh", path="/v1/auth")


@router.get("/me", response_model=out.User)
async def me(user=Depends(current_user), db=Depends(get_session, scope="function")):
    return await service.me(db, user)


@router.patch("/me", response_model=out.User)
async def edit_me(
    body: s.ProfileInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.edit_me(db, user, body)


@router.delete("/me", status_code=204)
async def delete_me(
    body: s.DeleteAccountInput, user=Depends(current_user), db=Depends(get_session, scope="function")
):
    return await service.delete_me(db, user, body)

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.encoders import ENCODERS_BY_TYPE
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from marcus.catalog import api as catalog
from marcus.community import discovery, engagement
from marcus.core.config import settings
from marcus.editorials import api as editorials
from marcus.identity import api as identity
from marcus.media import api as media
from marcus.moderation import api as moderation
from marcus.notes import api as notes

ENCODERS_BY_TYPE[datetime] = lambda value: (
    value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    if value.tzinfo is None
    else value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
)


def create_app():
    app = FastAPI(title="Marcus API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Requested-With"],
    )

    @app.middleware("http")
    async def request_id(request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def error(request, status, code, message, details=None):
        return JSONResponse(
            status_code=status,
            content={
                "error": {"code": code, "message": message, "details": details or {}},
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        detail = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"code": "request_failed", "message": str(exc.detail)}
        )
        return error(
            request,
            exc.status_code,
            detail.get("code", "request_failed"),
            detail.get("message", "请求未完成"),
            detail.get("details"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error(
            request,
            422,
            "validation_error",
            "请求字段不符合要求",
            [{"loc": list(e["loc"]), "message": e["msg"]} for e in exc.errors()],
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, exc):
        return error(request, 409, "data_conflict", "数据已变化或关联关系不成立")

    @app.exception_handler(OperationalError)
    async def database_error(request, exc):
        code = exc.orig.args[0] if getattr(exc.orig, "args", ()) else None
        if code in (1205, 1213):
            return error(request, 409, "concurrent_update", "内容正在更新，请保留修改并重试")
        return error(request, 503, "database_unavailable", "服务暂时不可用，请稍后重试")

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        import logging

        logging.getLogger("marcus.api").error(
            "request=%s failed type=%s", getattr(request.state, "request_id", None), type(exc).__name__
        )
        return error(request, 500, "internal_error", "服务暂时未能完成请求，请稍后重试")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    for module in (identity, catalog, media, notes, editorials, discovery, moderation, engagement):
        app.include_router(module.router, prefix="/v1")
    return app


app = create_app()

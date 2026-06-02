"""FastAPI exception handlers for VibeRoiError types.

Register on a FastAPI app:

    from viberoi_shared.errors.handlers import register_handlers
    register_handlers(app)

This module imports FastAPI, so import the handler explicitly via its
submodule path — don't surface it on `viberoi_shared.errors.__init__`
(keeps the lightweight exception types importable without FastAPI).
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from viberoi_shared.errors.types import VibeRoiError
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)


def _envelope(
    *,
    code: str,
    message: str,
    request_id: str | None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if request_id:
        error["request_id"] = request_id
    if details:
        error["details"] = details
    return {"error": error}


async def _viberoi_error_handler(request: Request, exc: VibeRoiError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "request_failed",
        error_code=exc.code,
        status=exc.status_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(
            code=exc.code,
            message=exc.safe_message,
            request_id=request_id,
            details=exc.details or None,
        ),
    )


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content=_envelope(
            code="validation_failed",
            message="Request validation failed.",
            request_id=request_id,
            details={"errors": exc.errors()},
        ),
    )


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(
            code="http_error",
            message=str(exc.detail) if exc.detail else "HTTP error.",
            request_id=request_id,
        ),
    )


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
    request_id = getattr(request.state, "request_id", None)
    logger.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content=_envelope(
            code="internal_error",
            message="Something went wrong.",
            request_id=request_id,
        ),
    )


def register_handlers(app: FastAPI) -> None:
    """Register all standard exception handlers on a FastAPI app."""
    app.add_exception_handler(VibeRoiError, _viberoi_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_handler)

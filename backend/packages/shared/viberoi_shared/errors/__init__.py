"""Typed exceptions + FastAPI handlers.

Services raise typed errors (`Unauthorized`, `Forbidden`, `NotFound`,
`Conflict`, `ValidationFailed`, `RateLimited`, `Unprocessable`) from
here. A registered FastAPI exception handler converts them into the
standard error envelope: `{ "error": { "code": ..., "message": ..., "request_id": ... } }`.

Never raise bare `HTTPException(400, "bad")` — use the typed exceptions.

For the FastAPI handler-registration helper, import it explicitly via:

    from viberoi_shared.errors.handlers import register_handlers

This keeps the lightweight exception types importable in modules that
do not depend on FastAPI (CLI tools, Lambdas, the agent's mock harness).
"""

from viberoi_shared.errors.types import (
    Conflict,
    ConfigError,
    ExternalServiceError,
    Forbidden,
    Gone,
    NotFound,
    RateLimited,
    Unauthorized,
    Unprocessable,
    ValidationFailed,
    VibeRoiError,
)

__all__ = [
    "Conflict",
    "ConfigError",
    "ExternalServiceError",
    "Forbidden",
    "Gone",
    "NotFound",
    "RateLimited",
    "Unauthorized",
    "Unprocessable",
    "ValidationFailed",
    "VibeRoiError",
]

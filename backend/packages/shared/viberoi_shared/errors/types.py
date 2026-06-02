"""Typed exceptions raised across the codebase.

Services raise these instead of bare `HTTPException`. The FastAPI
handler in `errors/handlers.py` converts them to the standard envelope:

    { "error": { "code": "...", "message": "...", "request_id": "..." } }

Each subclass declares its `code`, `status_code`, and `safe_message`
(the message returned to the client — never leaks internal details).
"""

from http import HTTPStatus
from typing import Any


class VibeRoiError(Exception):
    """Base for all typed errors."""

    code: str = "internal_error"
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    safe_message: str = "Something went wrong."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.safe_message)
        self.details: dict[str, Any] = details or {}


class Unauthorized(VibeRoiError):
    code = "unauthorized"
    status_code = HTTPStatus.UNAUTHORIZED
    safe_message = "Authentication required."


class Forbidden(VibeRoiError):
    code = "forbidden"
    status_code = HTTPStatus.FORBIDDEN
    safe_message = "You don't have access to this resource."


class NotFound(VibeRoiError):
    code = "not_found"
    status_code = HTTPStatus.NOT_FOUND
    safe_message = "Resource not found."


class Conflict(VibeRoiError):
    code = "conflict"
    status_code = HTTPStatus.CONFLICT
    safe_message = "Conflict with current state."


class ValidationFailed(VibeRoiError):
    code = "validation_failed"
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    safe_message = "Request validation failed."


class Unprocessable(VibeRoiError):
    code = "unprocessable"
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    safe_message = "Request cannot be processed."


class RateLimited(VibeRoiError):
    code = "rate_limited"
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    safe_message = "Rate limit exceeded. Try again later."


class ExternalServiceError(VibeRoiError):
    code = "external_service_error"
    status_code = HTTPStatus.BAD_GATEWAY
    safe_message = "An external service is unavailable."


class ConfigError(VibeRoiError):
    code = "config_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    safe_message = "Service is misconfigured."

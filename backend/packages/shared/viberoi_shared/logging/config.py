"""Structured logging via structlog.

Every log line gets `service`, `env`, plus any per-request contextvars
(`request_id`, `org_id`, `developer_id`) bound via `bind_request_context`.
A processor scrubs known PII field names from log payloads.

Usage:
    from viberoi_shared.logging import get_logger
    logger = get_logger(__name__)
    logger.info("session_received", session_id=sid, org_id=org_id)
"""

import logging
import sys
from typing import Any

import structlog

from viberoi_shared.config import Env, get_settings

# Field names whose VALUES never appear in logs. Anything keyed by one of
# these is replaced with `[REDACTED]` before the renderer sees it.
_PII_FIELDS = frozenset(
    {
        "email",
        "full_name",
        "name",
        "github_username",
        "org_token",
        "token",
        "password",
        "jwt",
        "authorization",
        "secret",
        "api_key",
        "webhook_url",
        "phone",
        "billing_email",
    }
)


def _scrub_pii(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict.keys()):
        if key.lower() in _PII_FIELDS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def _add_service_context(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    event_dict.setdefault("service", settings.service_name)
    event_dict.setdefault("env", settings.env.value)
    return event_dict


def configure_logging() -> None:
    """Configure structlog. Idempotent — safe to call multiple times."""
    settings = get_settings()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_service_context,
        _scrub_pii,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.env in (Env.DEV, Env.TEST):
        renderer: Any = structlog.dev.ConsoleRenderer(colors=False)
    else:
        renderer = structlog.processors.JSONRenderer()

    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger. Configures structlog on first call."""
    if not structlog.is_configured():
        configure_logging()
    return structlog.get_logger(name)


def bind_request_context(
    *,
    request_id: str,
    org_id: str | None = None,
    developer_id: str | None = None,
) -> None:
    """Bind per-request context vars; visible on every subsequent log line."""
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        org_id=org_id,
        developer_id=developer_id,
    )


def clear_request_context() -> None:
    """Clear all bound request context vars. Call at end of request lifecycle."""
    structlog.contextvars.clear_contextvars()

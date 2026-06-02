"""Structured logging via structlog + PII scrubbing.

Every log line gets `request_id`, `org_id`, `service`, `event`.
A pre-configured processor scrubs known PII fields (email, name, token).

Use the bound logger: `from viberoi_shared.logging import get_logger`.
Do NOT use stdlib `logging` directly; do NOT `print()`.
"""

from viberoi_shared.logging.config import (
    bind_request_context,
    clear_request_context,
    configure_logging,
    get_logger,
)

__all__ = [
    "bind_request_context",
    "clear_request_context",
    "configure_logging",
    "get_logger",
]

"""Request-ID middleware — binds per-request log context for the lifetime of a request.

Generates a UUIDv4 `request_id` if the inbound request doesn't carry one,
binds it (plus optional `org_id` / `developer_id` later set by handlers)
into structlog contextvars, and echoes the id back as `X-Request-ID` so
the client can correlate with our logs.

Install once per FastAPI app:

    from viberoi_shared.logging.middleware import RequestIdMiddleware
    app.add_middleware(RequestIdMiddleware)
"""

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from viberoi_shared.logging.config import bind_request_context, clear_request_context

HEADER_NAME = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Per-request context binding for structured logs."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(HEADER_NAME) or str(uuid.uuid4())
        request.state.request_id = request_id
        bind_request_context(request_id=request_id)
        try:
            response = await call_next(request)
            response.headers[HEADER_NAME] = request_id
            return response
        finally:
            clear_request_context()

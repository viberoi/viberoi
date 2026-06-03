"""Async HTTP client factory for outbound provider calls.

One `httpx.AsyncClient` per process, reused across requests. Standard
timeouts and a small in-process retry layer for transient 5xx/timeouts.
Structured logging on every request (method, host, path, status, ms).

This is the ONLY file in the Integration service that's allowed to
import `httpx` directly — per-provider adapters call `get_http_client()`.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from viberoi_shared.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
_DEFAULT_LIMITS = httpx.Limits(max_connections=50, max_keepalive_connections=20)

_RETRY_STATUS_CODES = frozenset({500, 502, 503, 504})
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 0.25  # 0.25s, 0.5s, 1.0s — capped at 3 attempts

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return the process-wide AsyncClient. Idempotent."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            limits=_DEFAULT_LIMITS,
            follow_redirects=False,
            headers={"User-Agent": "VibeROI-Integration/0.1"},
        )
    return _client


async def aclose() -> None:
    """Close the client on shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@asynccontextmanager
async def _trace(method: str, url: str) -> AsyncIterator[dict[str, Any]]:
    """Log start + end with duration_ms. Yields a mutable dict so caller
    can stash the response status into it for the final log line."""
    started = time.perf_counter()
    parsed = httpx.URL(url)
    bag: dict[str, Any] = {"host": parsed.host, "path": parsed.path}
    try:
        yield bag
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "http_request",
            method=method,
            host=bag["host"],
            path=bag["path"],
            status=bag.get("status"),
            duration_ms=duration_ms,
            attempts=bag.get("attempts", 1),
        )


async def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json: Any = None,
    params: dict[str, Any] | None = None,
    content: bytes | None = None,
) -> httpx.Response:
    """Send a request with retries on transient 5xx + timeouts.

    4xx responses are returned directly — caller decides how to handle
    (e.g. 401 might trigger token refresh, 429 trips the circuit breaker).
    """
    client = get_http_client()
    last_exc: Exception | None = None

    async with _trace(method, url) as bag:
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            bag["attempts"] = attempt
            try:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    params=params,
                    content=content,
                )
                bag["status"] = response.status_code
                if response.status_code in _RETRY_STATUS_CODES and attempt < _RETRY_ATTEMPTS:
                    await _sleep_backoff(attempt)
                    continue
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exc = e
                if attempt < _RETRY_ATTEMPTS:
                    await _sleep_backoff(attempt)
                    continue
                bag["status"] = "network_error"
                raise

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("unreachable: request loop exhausted without return")


async def _sleep_backoff(attempt: int) -> None:
    import asyncio

    await asyncio.sleep(_RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

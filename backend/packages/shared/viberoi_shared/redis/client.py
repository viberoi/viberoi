"""Async Redis client factory.

One client per process; lazily initialized. `aclose()` cleans up on
shutdown. Configured with conservative timeouts so a dead Redis fails
fast instead of hanging requests.
"""

import redis.asyncio as aioredis

from viberoi_shared.config import get_settings

_client: aioredis.Redis | None = None


def get_client() -> aioredis.Redis:
    """Return the process-wide async Redis client. Idempotent."""
    global _client
    if _client is None:
        s = get_settings()
        _client = aioredis.from_url(
            s.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
    return _client


async def aclose() -> None:
    """Close the client (call on shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

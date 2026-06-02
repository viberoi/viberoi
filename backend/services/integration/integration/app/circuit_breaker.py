"""Per (org, provider) circuit breaker on Redis.

Tracks consecutive failures with a 5-minute rolling counter. After
`OPEN_THRESHOLD` failures, opens the circuit for `OPEN_DURATION_S`.
During the open window, callers should fail fast (raise `RateLimited`)
rather than make another doomed outbound call.

Keys:
  cb:{org_id}:{provider}:failures   INCR with 5-min EXPIRE
  cb:{org_id}:{provider}:open       SET EX (15 min) when threshold hit

`record_success()` resets both (the circuit closes immediately on the
first success).
"""

from __future__ import annotations

from uuid import UUID

from viberoi_shared.logging import get_logger
from viberoi_shared.redis import get_client

logger = get_logger(__name__)

OPEN_THRESHOLD = 3
FAILURE_WINDOW_S = 300  # 5 minutes
OPEN_DURATION_S = 900  # 15 minutes


def _failure_key(org_id: UUID | str, provider: str) -> str:
    return f"cb:{org_id}:{provider}:failures"


def _open_key(org_id: UUID | str, provider: str) -> str:
    return f"cb:{org_id}:{provider}:open"


async def is_open(org_id: UUID | str, provider: str) -> bool:
    """True if the circuit is currently open and outbound calls should fail fast."""
    client = get_client()
    return bool(await client.exists(_open_key(org_id, provider)))


async def record_failure(org_id: UUID | str, provider: str) -> bool:
    """Increment the failure counter. Returns True if this call opened the circuit."""
    client = get_client()
    fail_key = _failure_key(org_id, provider)
    async with client.pipeline(transaction=False) as pipe:
        pipe.incr(fail_key)
        pipe.expire(fail_key, FAILURE_WINDOW_S)
        results = await pipe.execute()
    count = int(results[0])
    if count >= OPEN_THRESHOLD:
        await client.set(_open_key(org_id, provider), "1", ex=OPEN_DURATION_S)
        logger.warning(
            "circuit_opened",
            org_id=str(org_id),
            provider=provider,
            failure_count=count,
        )
        return True
    return False


async def record_success(org_id: UUID | str, provider: str) -> None:
    """Reset the counter and close the circuit (idempotent)."""
    client = get_client()
    await client.delete(_failure_key(org_id, provider), _open_key(org_id, provider))


async def force_open(
    org_id: UUID | str, provider: str, *, duration_s: int = OPEN_DURATION_S
) -> None:
    """Manually open the circuit — useful when a token is known-revoked."""
    client = get_client()
    await client.set(_open_key(org_id, provider), "1", ex=duration_s)

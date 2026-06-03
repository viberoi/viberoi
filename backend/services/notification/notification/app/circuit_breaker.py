"""Per-(org, channel) circuit breaker backed by Redis.

State key: `notif:cb:{org}:{channel}` → JSON `{failures, opened_at}`.
Thresholds match what the Integration service uses for its provider
breakers, so behaviour is predictable across the platform.

Operation:
  - On every failure, increment `failures` and refresh the key TTL.
  - When `failures >= FAILURE_THRESHOLD`, set `opened_at` to now.
  - `is_open` returns True for `OPEN_WINDOW_SECONDS` after `opened_at`.
  - `record_success` deletes the key.
"""

from __future__ import annotations

import time
from uuid import UUID

import orjson

from viberoi_shared.logging import get_logger
from viberoi_shared.redis import get_client

logger = get_logger(__name__)

FAILURE_THRESHOLD = 3
OPEN_WINDOW_SECONDS = 15 * 60
KEY_TTL_SECONDS = OPEN_WINDOW_SECONDS + 60


def _key(org_id: UUID | str, channel: str) -> str:
    return f"notif:cb:{org_id}:{channel}"


async def is_open(org_id: UUID, channel: str) -> bool:
    client = get_client()
    raw = await client.get(_key(org_id, channel))
    if raw is None:
        return False
    try:
        state = orjson.loads(raw)
    except orjson.JSONDecodeError:
        return False
    opened_at = state.get("opened_at")
    if opened_at is None:
        return False
    return (time.time() - float(opened_at)) < OPEN_WINDOW_SECONDS


async def record_failure(org_id: UUID, channel: str) -> int:
    """Return the new failure count."""
    client = get_client()
    key = _key(org_id, channel)
    raw = await client.get(key)
    state: dict[str, float] = {"failures": 0.0, "opened_at": 0.0}
    if raw is not None:
        try:
            state.update(orjson.loads(raw))
        except orjson.JSONDecodeError:
            pass
    failures = int(state.get("failures", 0)) + 1
    state["failures"] = failures
    if failures >= FAILURE_THRESHOLD and not state.get("opened_at"):
        state["opened_at"] = time.time()
        logger.warning(
            "notification_circuit_opened",
            org_id=str(org_id),
            channel=channel,
            failures=failures,
        )
    await client.set(key, orjson.dumps(state).decode(), ex=KEY_TTL_SECONDS)
    return failures


async def record_success(org_id: UUID, channel: str) -> None:
    client = get_client()
    await client.delete(_key(org_id, channel))

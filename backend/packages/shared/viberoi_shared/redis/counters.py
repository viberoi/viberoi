"""Per-org KPI counters in Redis.

Keys: `org:{org_id}:kpi:{kpi_type}:{day}` where `day` is UTC `YYYY-MM-DD`.
TTL: 7 days — historical data persists in Postgres `kpi_snapshots`;
Redis is the live counter layer that drives the dashboard's SSE updates.

Cost is stored as integer **cents** (Redis `INCRBY`) to avoid float
drift; reads divide by 100. The dashboard layer formats for display.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from viberoi_shared.redis.client import get_client

# 7 days of live counters; older data is in Postgres snapshots.
COUNTER_TTL_SECONDS = 7 * 24 * 60 * 60

_KPI_SESSION_COUNT = "session_count"
_KPI_COST_CENTS = "cost_cents"


def _today_utc() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def _key(org_id: UUID | str, kpi_type: str, day: str | None = None) -> str:
    return f"org:{org_id}:kpi:{kpi_type}:{day or _today_utc()}"


async def incr_session_count(org_id: UUID | str, day: str | None = None) -> int:
    """Increment today's session count for an org. Returns new value."""
    client = get_client()
    key = _key(org_id, _KPI_SESSION_COUNT, day)
    async with client.pipeline(transaction=False) as pipe:
        pipe.incr(key)
        pipe.expire(key, COUNTER_TTL_SECONDS)
        results = await pipe.execute()
    return int(results[0])


async def incr_cost_usd(
    org_id: UUID | str,
    amount_usd: Decimal | float,
    day: str | None = None,
) -> int:
    """Add to today's cost total. Stored as integer cents.

    Returns the new total in cents. Negative or zero amounts are a no-op
    (returns current value without writing).
    """
    cents = int(round(float(amount_usd) * 100))
    client = get_client()
    key = _key(org_id, _KPI_COST_CENTS, day)

    if cents <= 0:
        current = await client.get(key)
        return int(current or 0)

    async with client.pipeline(transaction=False) as pipe:
        pipe.incrby(key, cents)
        pipe.expire(key, COUNTER_TTL_SECONDS)
        results = await pipe.execute()
    return int(results[0])


async def get_today_summary(org_id: UUID | str) -> dict[str, Any]:
    """Return today's counters for an org. Used by the API service for
    live KPI cards on the dashboard."""
    client = get_client()
    sessions_key = _key(org_id, _KPI_SESSION_COUNT)
    cost_key = _key(org_id, _KPI_COST_CENTS)
    sessions, cents = await client.mget(sessions_key, cost_key)
    return {
        "day": _today_utc(),
        "sessions": int(sessions or 0),
        "cost_usd": float(int(cents or 0)) / 100.0,
    }


async def reset_org_counters(org_id: UUID | str, day: str | None = None) -> None:
    """Delete today's counter keys for an org. For tests; not used in prod."""
    client = get_client()
    keys = [
        _key(org_id, _KPI_SESSION_COUNT, day),
        _key(org_id, _KPI_COST_CENTS, day),
    ]
    await client.delete(*keys)

"""Redis adapter — counters, caching, and pub/sub.

Keys are namespaced per org: `org:{org_id}:kpi:{type}:{day}`.
Pub/sub channels drive SSE live updates on the dashboard (lands in Slice 6).
"""

from viberoi_shared.redis.client import aclose, get_client
from viberoi_shared.redis.counters import (
    COUNTER_TTL_SECONDS,
    get_today_summary,
    incr_cost_usd,
    incr_session_count,
    reset_org_counters,
)

__all__ = [
    "COUNTER_TTL_SECONDS",
    "aclose",
    "get_client",
    "get_today_summary",
    "incr_cost_usd",
    "incr_session_count",
    "reset_org_counters",
]

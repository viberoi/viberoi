"""Redis adapter — counters, caching, and pub/sub.

Keys are namespaced per org: `org:{org_id}:kpi:{type}`.
Pub/sub channels drive SSE live updates on the dashboard.
"""

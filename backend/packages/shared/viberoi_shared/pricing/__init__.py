"""Per-model pricing for cost reconciliation.

The agent sends `total_cost_usd=0` by design — pricing is volatile and
shouldn't be hardcoded into the agent. The Worker reconciles via this
module on every session insert.

`compute_cost(tool_name, model, tokens, pricing_type)` returns
`(cost_usd, is_estimated)`. Subscription tools (Claude Pro, Cursor,
Copilot) still get an as-if-API-rate cost so dashboards can compare
ROI across tools on the same scale — `is_estimated=True` flags this.
"""

from viberoi_shared.pricing.rates import (
    RATE_TABLE,
    compute_cost,
)

__all__ = ["RATE_TABLE", "compute_cost"]

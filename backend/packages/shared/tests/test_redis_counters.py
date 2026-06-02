"""Redis counter helpers — integration tests (requires Redis from docker-compose)."""

from decimal import Decimal
from uuid import uuid4

import pytest

from viberoi_shared.redis import (
    get_today_summary,
    incr_cost_usd,
    incr_session_count,
    reset_org_counters,
)

pytestmark = pytest.mark.integration


async def test_session_count_increments() -> None:
    org_id = uuid4()
    await reset_org_counters(org_id)

    first = await incr_session_count(org_id)
    second = await incr_session_count(org_id)
    third = await incr_session_count(org_id)

    assert first == 1
    assert second == 2
    assert third == 3

    summary = await get_today_summary(org_id)
    assert summary["sessions"] == 3


async def test_cost_increments_avoid_float_drift() -> None:
    """Three increments of 0.0042 = 0.0126 — stored as 1 cent (rounded down)."""
    org_id = uuid4()
    await reset_org_counters(org_id)

    await incr_cost_usd(org_id, Decimal("0.0042"))  # 0 cents (rounds to 0)
    await incr_cost_usd(org_id, Decimal("0.50"))  # 50 cents
    await incr_cost_usd(org_id, Decimal("1.499"))  # 150 cents (rounded)

    summary = await get_today_summary(org_id)
    # 0 + 50 + 150 = 200 cents = $2.00
    assert summary["cost_usd"] == pytest.approx(2.00, abs=0.01)


async def test_zero_or_negative_cost_is_noop() -> None:
    org_id = uuid4()
    await reset_org_counters(org_id)

    result = await incr_cost_usd(org_id, Decimal("0"))
    assert result == 0

    result = await incr_cost_usd(org_id, Decimal("-1.5"))
    assert result == 0

    summary = await get_today_summary(org_id)
    assert summary["cost_usd"] == 0.0


async def test_counters_are_per_org() -> None:
    org_a = uuid4()
    org_b = uuid4()
    await reset_org_counters(org_a)
    await reset_org_counters(org_b)

    await incr_session_count(org_a)
    await incr_session_count(org_a)
    await incr_session_count(org_b)

    summary_a = await get_today_summary(org_a)
    summary_b = await get_today_summary(org_b)

    assert summary_a["sessions"] == 2
    assert summary_b["sessions"] == 1


async def test_empty_summary_for_new_org() -> None:
    org_id = uuid4()  # never had any activity
    summary = await get_today_summary(org_id)
    assert summary["sessions"] == 0
    assert summary["cost_usd"] == 0.0

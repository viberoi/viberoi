"""Tests for the per-(org, channel) circuit breaker.

Marked integration — relies on the real Redis from docker-compose.
The same pattern as the Integration service's circuit-breaker tests.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from notification.app.circuit_breaker import (
    FAILURE_THRESHOLD,
    is_open,
    record_failure,
    record_success,
)

pytestmark = pytest.mark.integration


async def test_starts_closed() -> None:
    assert await is_open(uuid4(), "slack") is False


async def test_opens_after_threshold() -> None:
    org = uuid4()
    for _ in range(FAILURE_THRESHOLD - 1):
        await record_failure(org, "slack")
    assert await is_open(org, "slack") is False
    await record_failure(org, "slack")
    assert await is_open(org, "slack") is True


async def test_success_resets() -> None:
    org = uuid4()
    for _ in range(FAILURE_THRESHOLD):
        await record_failure(org, "slack")
    assert await is_open(org, "slack") is True
    await record_success(org, "slack")
    assert await is_open(org, "slack") is False

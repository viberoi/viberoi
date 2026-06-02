"""Circuit breaker tests — integration tests against the dev Redis."""

from uuid import uuid4

import pytest

from integration.app import circuit_breaker as cb

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _reset_breaker() -> None:
    """Use a unique org per test for isolation; no explicit cleanup needed."""
    yield


async def test_initially_closed() -> None:
    org = uuid4()
    assert not await cb.is_open(org, "github")


async def test_single_failure_does_not_open() -> None:
    org = uuid4()
    opened = await cb.record_failure(org, "github")
    assert opened is False
    assert not await cb.is_open(org, "github")


async def test_threshold_failures_open_circuit() -> None:
    org = uuid4()
    for _ in range(cb.OPEN_THRESHOLD - 1):
        await cb.record_failure(org, "linear")
    # Last one trips it
    opened = await cb.record_failure(org, "linear")
    assert opened is True
    assert await cb.is_open(org, "linear")


async def test_record_success_closes_circuit() -> None:
    org = uuid4()
    for _ in range(cb.OPEN_THRESHOLD):
        await cb.record_failure(org, "jira")
    assert await cb.is_open(org, "jira")
    await cb.record_success(org, "jira")
    assert not await cb.is_open(org, "jira")


async def test_failures_isolated_per_org() -> None:
    org_a = uuid4()
    org_b = uuid4()
    for _ in range(cb.OPEN_THRESHOLD):
        await cb.record_failure(org_a, "github")
    assert await cb.is_open(org_a, "github")
    assert not await cb.is_open(org_b, "github")


async def test_failures_isolated_per_provider() -> None:
    org = uuid4()
    for _ in range(cb.OPEN_THRESHOLD):
        await cb.record_failure(org, "github")
    assert await cb.is_open(org, "github")
    assert not await cb.is_open(org, "linear")


async def test_force_open_with_custom_duration() -> None:
    org = uuid4()
    await cb.force_open(org, "github", duration_s=120)
    assert await cb.is_open(org, "github")

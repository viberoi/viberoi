"""OAuth state store — integration tests against the dev Redis."""

from uuid import uuid4

import pytest

from viberoi_shared.integrations.oauth_state import (
    STATE_TTL_SECONDS,
    OAuthStateError,
    consume,
    generate_token,
    store,
)

pytestmark = pytest.mark.integration


async def test_generate_token_is_unique_and_url_safe() -> None:
    a = generate_token()
    b = generate_token()
    assert a != b
    # URL-safe: only alphanum + -_
    assert all(c.isalnum() or c in "-_" for c in a)
    assert len(a) >= 30


async def test_store_and_consume_round_trip() -> None:
    state = generate_token()
    org_id = uuid4()
    dev_id = uuid4()
    await store(state, org_id=org_id, developer_id=dev_id, provider="github")
    payload = await consume(state)
    assert payload["org_id"] == str(org_id)
    assert payload["developer_id"] == str(dev_id)
    assert payload["provider"] == "github"


async def test_consume_is_single_use() -> None:
    state = generate_token()
    await store(state, org_id=uuid4(), developer_id=uuid4(), provider="linear")
    await consume(state)
    with pytest.raises(OAuthStateError):
        await consume(state)


async def test_consume_missing_state_raises() -> None:
    with pytest.raises(OAuthStateError):
        await consume(generate_token())


async def test_consume_empty_state_raises() -> None:
    with pytest.raises(OAuthStateError):
        await consume("")


async def test_state_expires_via_ttl() -> None:
    """Verifies that the TTL setting is applied (via redis.ttl())."""
    from viberoi_shared.redis import get_client

    state = generate_token()
    await store(state, org_id=uuid4(), developer_id=uuid4(), provider="jira")
    client = get_client()
    ttl = await client.ttl(f"oauth:state:{state}")
    # Redis returns seconds-to-expire; should be within tolerance of our TTL
    assert 0 < ttl <= STATE_TTL_SECONDS

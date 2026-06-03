"""Orchestrator tests — integration-marked (uses real Postgres + Redis +
LocalStack KMS via shared fixtures)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from integration.app import orchestrator
from integration.app.providers import registry
from integration.app.providers.base import (
    ProviderConnection,
    WebhookRegistration,
    WebhookRegistrationError,
)
from sqlalchemy import text

from viberoi_shared.db import superuser_session
from viberoi_shared.errors import NotFound
from viberoi_shared.integrations.oauth_state import OAuthStateError
from viberoi_shared.orgs.models import Developer, Org

pytestmark = pytest.mark.integration


# ── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
async def org_and_dev() -> tuple[Org, Developer]:
    org_id = uuid4()
    dev_id = uuid4()
    async with superuser_session() as db:
        org = Org(
            id=org_id,
            domain=f"orch-{uuid4().hex[:8]}.test",
            name_ciphertext=b"\x00\x00\x00\x04fake",
            name_key_version=1,
            name_iv=b"\x00" * 12,
        )
        db.add(org)
        await db.flush()
        dev = Developer(
            id=dev_id,
            org_id=org_id,
            cognito_sub=f"cog-orch-{uuid4()}",
            email_ciphertext=b"\x00\x00\x00\x04fake",
            email_key_version=1,
            email_iv=b"\x00" * 12,
            email_hash=uuid4().bytes,
        )
        db.add(dev)
        await db.flush()

    yield (org, dev)

    async with superuser_session() as db:
        await db.execute(
            text(
                "DELETE FROM integration_oauth_tokens WHERE org_id = :id"
            ),
            {"id": str(org_id)},
        )
        await db.execute(
            text("DELETE FROM orgs WHERE id = :id"), {"id": str(org_id)}
        )


def _mock_adapter(
    *,
    authorize_url: str = "https://provider.example.com/auth?state=x",
    callback_return: ProviderConnection | None = None,
    webhook_return: WebhookRegistration | None = None,
    webhook_raises: bool = False,
) -> MagicMock:
    """Build a mock ProviderAdapter that satisfies the contract."""
    adapter = MagicMock()
    adapter.authorize_url = MagicMock(return_value=authorize_url)
    adapter.complete_callback = AsyncMock(
        return_value=callback_return
        or ProviderConnection(
            access_token="at_test",
            refresh_token="rt_test",
            expires_at=None,
            scope="read",
            installation_id="123",
            extra={"cloud_id": "cloud-1"},
        )
    )
    if webhook_raises:
        adapter.register_webhook = AsyncMock(
            side_effect=WebhookRegistrationError("provider rejected")
        )
    else:
        adapter.register_webhook = AsyncMock(
            return_value=webhook_return
            or WebhookRegistration(
                provider_webhook_ids=["wh_1"], secret="sec_1"
            )
        )
    adapter.revoke = AsyncMock(return_value=None)
    return adapter


@pytest.fixture
def with_mocked_provider(monkeypatch: pytest.MonkeyPatch):
    """Override the registry with a mock provider; return the mock so tests
    can configure return values + inspect calls."""
    adapter = _mock_adapter()
    registry.reset()
    registry.override_for_test("github", adapter)
    registry.override_for_test("jira", adapter)
    registry.override_for_test("linear", adapter)
    yield adapter
    registry.reset()


@pytest.fixture
def mock_sqs(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Mock SQS publish so the test doesn't depend on LocalStack SQS state."""
    mock = AsyncMock(return_value="mock-msg-id")
    monkeypatch.setattr(orchestrator, "sqs_publish", mock)
    return mock


# ── initiate_connect ───────────────────────────────────────────────────────


async def test_initiate_connect_returns_authorize_url(
    org_and_dev: tuple[Org, Developer],
    with_mocked_provider: MagicMock,
) -> None:
    org, dev = org_and_dev
    result = await orchestrator.initiate_connect(
        org_id=org.id,
        developer_id=dev.id,
        provider="github",
        redirect_uri="https://api/cb",
    )
    assert result.authorize_url == "https://provider.example.com/auth?state=x"
    with_mocked_provider.authorize_url.assert_called_once()
    # State was passed through
    state_kwarg = with_mocked_provider.authorize_url.call_args.kwargs["state"]
    assert isinstance(state_kwarg, str)
    assert len(state_kwarg) > 20


# ── complete_connect ───────────────────────────────────────────────────────


async def test_complete_connect_happy_path(
    org_and_dev: tuple[Org, Developer],
    with_mocked_provider: MagicMock,
    mock_sqs: AsyncMock,
) -> None:
    org, dev = org_and_dev

    # Step 1: initiate (gets us a real state in Redis)
    init = await orchestrator.initiate_connect(
        org_id=org.id,
        developer_id=dev.id,
        provider="linear",
        redirect_uri="https://api/cb",
    )
    state = init.authorize_url.rsplit("=", 1)[-1]  # mock embeds state in URL
    # The mock returns a fixed url, so we need to pull state another way.
    # Better: introspect the mock's last call args.
    state = with_mocked_provider.authorize_url.call_args.kwargs["state"]

    # Step 2: simulate the provider redirect
    result = await orchestrator.complete_connect(
        provider="linear",
        callback_params={"code": "abc", "state": state},
        redirect_uri="https://api/cb",
        webhook_base_url="https://hooks.viberoi.io",
    )
    assert result.webhook_registration_status == "ok"
    assert result.integration_id is not None

    # Verify the provider's register_webhook was called with our integration_id
    reg_call = with_mocked_provider.register_webhook.call_args
    assert (
        f"https://hooks.viberoi.io/webhooks/linear/{result.integration_id}"
        == reg_call.kwargs["webhook_url"]
    )

    # Verify SQS publish was called with the initial backfill envelope
    sqs_call = mock_sqs.call_args
    assert sqs_call.args[0] == "backfill_jobs"
    body = sqs_call.args[1]
    assert body["provider"] == "linear"
    assert body["org_id"] == str(org.id)
    assert body["sync_type"] == "initial_90d"


async def test_complete_connect_with_bad_state_raises(
    org_and_dev: tuple[Org, Developer],
    with_mocked_provider: MagicMock,
    mock_sqs: AsyncMock,
) -> None:
    with pytest.raises(OAuthStateError):
        await orchestrator.complete_connect(
            provider="github",
            callback_params={"code": "x", "state": "not-a-real-state"},
            redirect_uri="https://api/cb",
            webhook_base_url="https://hooks.viberoi.io",
        )


async def test_complete_connect_provider_mismatch_raises(
    org_and_dev: tuple[Org, Developer],
    with_mocked_provider: MagicMock,
    mock_sqs: AsyncMock,
) -> None:
    """Callback hits a different provider than the one state was bound to."""
    org, dev = org_and_dev
    init = await orchestrator.initiate_connect(
        org_id=org.id,
        developer_id=dev.id,
        provider="github",
        redirect_uri="https://api/cb",
    )
    state = with_mocked_provider.authorize_url.call_args.kwargs["state"]

    with pytest.raises(OAuthStateError):
        await orchestrator.complete_connect(
            provider="linear",  # ≠ "github" from state
            callback_params={"code": "x", "state": state},
            redirect_uri="https://api/cb",
            webhook_base_url="https://hooks.viberoi.io",
        )


async def test_complete_connect_webhook_failure_still_persists_token(
    org_and_dev: tuple[Org, Developer],
    monkeypatch: pytest.MonkeyPatch,
    mock_sqs: AsyncMock,
) -> None:
    """Webhook registration failure leaves the integration in 'failed' state
    but does NOT roll back the token storage — user can re-attempt via /sync."""
    org, dev = org_and_dev
    adapter = _mock_adapter(webhook_raises=True)
    registry.reset()
    registry.override_for_test("jira", adapter)

    init = await orchestrator.initiate_connect(
        org_id=org.id,
        developer_id=dev.id,
        provider="jira",
        redirect_uri="https://api/cb",
    )
    state = adapter.authorize_url.call_args.kwargs["state"]

    result = await orchestrator.complete_connect(
        provider="jira",
        callback_params={"code": "abc", "state": state},
        redirect_uri="https://api/cb",
        webhook_base_url="https://hooks.viberoi.io",
    )
    assert result.webhook_registration_status == "failed"
    assert result.integration_id is not None
    registry.reset()


# ── disconnect ─────────────────────────────────────────────────────────────


async def test_disconnect_unknown_integration_raises(
    org_and_dev: tuple[Org, Developer],
    with_mocked_provider: MagicMock,
) -> None:
    org, _ = org_and_dev
    with pytest.raises(NotFound):
        await orchestrator.disconnect(org_id=org.id, provider="github")


async def test_disconnect_revokes_locally_and_calls_provider(
    org_and_dev: tuple[Org, Developer],
    with_mocked_provider: MagicMock,
    mock_sqs: AsyncMock,
) -> None:
    org, dev = org_and_dev

    # Set up an integration first
    init = await orchestrator.initiate_connect(
        org_id=org.id, developer_id=dev.id, provider="github", redirect_uri="x"
    )
    state = with_mocked_provider.authorize_url.call_args.kwargs["state"]
    await orchestrator.complete_connect(
        provider="github",
        callback_params={"installation_id": "999", "state": state},
        redirect_uri="x",
        webhook_base_url="https://hooks",
    )
    with_mocked_provider.revoke.reset_mock()

    await orchestrator.disconnect(org_id=org.id, provider="github")

    # Provider's revoke was called
    with_mocked_provider.revoke.assert_called_once()

    # Re-disconnect should now 404 (already revoked)
    with pytest.raises(NotFound):
        await orchestrator.disconnect(org_id=org.id, provider="github")


# ── list_integrations ──────────────────────────────────────────────────────


async def test_list_integrations_returns_active_rows(
    org_and_dev: tuple[Org, Developer],
    with_mocked_provider: MagicMock,
    mock_sqs: AsyncMock,
) -> None:
    org, dev = org_and_dev

    init = await orchestrator.initiate_connect(
        org_id=org.id, developer_id=dev.id, provider="linear", redirect_uri="x"
    )
    state = with_mocked_provider.authorize_url.call_args.kwargs["state"]
    await orchestrator.complete_connect(
        provider="linear",
        callback_params={"code": "abc", "state": state},
        redirect_uri="x",
        webhook_base_url="https://hooks",
    )

    rows = await orchestrator.list_integrations(org_id=org.id)
    assert len(rows) == 1
    assert rows[0]["provider"] == "linear"
    assert rows[0]["revoked"] is False
    assert rows[0]["webhook_registration_status"] == "ok"

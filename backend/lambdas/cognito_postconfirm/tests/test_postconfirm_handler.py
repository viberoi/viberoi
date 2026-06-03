"""Unit tests for the PostConfirmation handler.

Mocks all DB + crypto + Cognito SDK calls; we just verify the
provisioning logic (first-user vs invited, idempotency, attr write).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cognito_postconfirm import handler as handler_mod
from cognito_postconfirm.handler import (
    ROLE_FIRST_USER,
    ROLE_INVITED,
    PostConfirmationError,
    handler,
)


def _event(email: str = "alice@acme.com", sub: str | None = None) -> dict[str, Any]:
    return {
        "version": "1",
        "region": "us-east-1",
        "userPoolId": "us-east-1_TEST123456",
        "userName": "alice",
        "callerContext": {"awsSdkVersion": "x", "clientId": "stub-client"},
        "triggerSource": "PostConfirmation_ConfirmSignUp",
        "request": {
            "userAttributes": {
                "sub": sub or "cog-sub-123",
                "email": email,
                "email_verified": "true",
            },
        },
        "response": {},
    }


@pytest.fixture
def patched(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock every external boundary the handler touches."""
    fake_db = MagicMock()

    class _Ctx:
        async def __aenter__(self):
            return fake_db

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(handler_mod, "superuser_session", lambda: _Ctx())

    encrypted = MagicMock()
    encrypted.ciphertext = b"ct"
    encrypted.key_version = 1
    encrypted.iv = b"iv"
    monkeypatch.setattr(handler_mod, "encrypt_pii", AsyncMock(return_value=encrypted))
    monkeypatch.setattr(handler_mod, "hmac_for_lookup", AsyncMock(return_value=b"\x00" * 32))

    get_dev = AsyncMock(return_value=None)
    create_org = AsyncMock()
    lock_org = AsyncMock()
    count_devs = AsyncMock(return_value=0)
    new_dev = MagicMock()
    new_dev.id = uuid4()
    create_dev = AsyncMock(return_value=new_dev)

    monkeypatch.setattr(handler_mod, "get_developer_by_cognito_sub", get_dev)
    monkeypatch.setattr(handler_mod, "create_org_if_missing", create_org)
    monkeypatch.setattr(handler_mod, "lock_org_for_update", lock_org)
    monkeypatch.setattr(handler_mod, "count_developers", count_devs)
    monkeypatch.setattr(handler_mod, "create_developer_if_missing", create_dev)

    return {
        "get_dev": get_dev,
        "create_org": create_org,
        "lock_org": lock_org,
        "count_devs": count_devs,
        "create_dev": create_dev,
    }


def test_first_user_gets_orgadmin(patched) -> None:
    org_id = uuid4()
    org = MagicMock()
    org.id = org_id
    patched["create_org"].return_value = org
    patched["count_devs"].return_value = 0  # first developer

    handler(_event(), None)

    patched["create_dev"].assert_awaited_once()
    kw = patched["create_dev"].call_args.kwargs
    assert kw["org_id"] == org_id
    assert kw["role"] == ROLE_FIRST_USER
    assert kw["cognito_sub"] == "cog-sub-123"


def test_invited_user_gets_developer(patched) -> None:
    org = MagicMock()
    org.id = uuid4()
    patched["create_org"].return_value = org
    patched["count_devs"].return_value = 3  # 3 existing developers

    handler(_event(), None)

    kw = patched["create_dev"].call_args.kwargs
    assert kw["role"] == ROLE_INVITED


def test_idempotent_when_developer_exists(patched) -> None:
    """Re-fired trigger → developer already exists → no row creation, attrs synced."""
    existing = MagicMock()
    existing.org_id = uuid4()
    existing.role = ROLE_FIRST_USER
    patched["get_dev"].return_value = existing

    result = handler(_event(), None)
    assert result["userName"] == "alice"
    patched["create_org"].assert_not_called()
    patched["create_dev"].assert_not_called()


def test_domain_extracted_from_email(patched) -> None:
    org = MagicMock()
    org.id = uuid4()
    patched["create_org"].return_value = org

    handler(_event(email="bob@SOME.Corp"), None)

    domain_kw = patched["create_org"].call_args.kwargs["domain"]
    assert domain_kw == "some.corp"


def test_wrong_trigger_source_rejected(patched) -> None:
    event = _event()
    event["triggerSource"] = "PostConfirmation_ConfirmForgotPassword"
    with pytest.raises(PostConfirmationError, match="Invalid invocation"):
        handler(event, None)


def test_wrong_user_pool_rejected(patched) -> None:
    event = _event()
    event["userPoolId"] = "us-east-1_OTHER000000"
    with pytest.raises(PostConfirmationError, match="Invalid invocation"):
        handler(event, None)


def test_missing_email_rejected(patched) -> None:
    event = _event()
    event["request"]["userAttributes"]["email"] = ""
    with pytest.raises(PostConfirmationError, match="missing"):
        handler(event, None)


def test_db_error_wrapped(monkeypatch: pytest.MonkeyPatch, patched) -> None:
    patched["create_org"].side_effect = RuntimeError("conn refused")
    with pytest.raises(PostConfirmationError, match="Provisioning failed") as excinfo:
        handler(_event(), None)
    # No DB internals leak
    assert "conn refused" not in str(excinfo.value)

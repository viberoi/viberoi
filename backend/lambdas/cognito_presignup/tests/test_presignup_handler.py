"""Unit tests for the PreSignUp handler.

DB layer is mocked — no real Postgres. Cognito event shape mirrors the
real PreSignUp_SignUp payload.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from cognito_presignup import handler as handler_mod
from cognito_presignup.handler import SignupRejected, handler


def _event(email: str) -> dict[str, Any]:
    return {
        "version": "1",
        "region": "us-east-1",
        "userPoolId": "us-east-1_TEST123456",
        "userName": "alice",
        "callerContext": {"awsSdkVersion": "x", "clientId": "stub-client"},
        "triggerSource": "PreSignUp_SignUp",
        "request": {
            "userAttributes": {"email": email},
            "validationData": {},
        },
        "response": {},
    }


@pytest.fixture
def _no_existing_org(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(handler_mod, "get_org_by_domain", mock)
    # Bypass real superuser_session
    class _Ctx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(handler_mod, "superuser_session", lambda: _Ctx())
    return mock


@pytest.fixture
def _existing_org(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value=object())  # any truthy
    monkeypatch.setattr(handler_mod, "get_org_by_domain", mock)

    class _Ctx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(handler_mod, "superuser_session", lambda: _Ctx())
    return mock


def test_business_email_accepted(_no_existing_org) -> None:
    event = _event("alice@acme.com")
    result = handler(event, None)
    assert result is event  # Cognito requires event echo


@pytest.mark.parametrize(
    "email",
    [
        "alice@gmail.com",
        "BOB@OUTLOOK.COM",  # case-insensitive
        "carol@yahoo.com",
        "dave@icloud.com",
        "eve@protonmail.com",
    ],
)
def test_consumer_domain_rejected(email: str, _no_existing_org) -> None:
    with pytest.raises(SignupRejected, match="work email"):
        handler(_event(email), None)


def test_existing_org_rejected(_existing_org) -> None:
    with pytest.raises(SignupRejected, match="already on VibeROI"):
        handler(_event("alice@acme.com"), None)


def test_missing_email_rejected(_no_existing_org) -> None:
    event = _event("")
    with pytest.raises(SignupRejected, match="Email"):
        handler(event, None)


def test_malformed_email_rejected(_no_existing_org) -> None:
    with pytest.raises(SignupRejected):
        handler(_event("notanemail"), None)


def test_wrong_trigger_source_rejected(_no_existing_org) -> None:
    event = _event("alice@acme.com")
    event["triggerSource"] = "PreSignUp_AdminCreateUser"  # not what we expect
    with pytest.raises(SignupRejected, match="Invalid signup"):
        handler(event, None)


def test_wrong_user_pool_rejected(_no_existing_org) -> None:
    event = _event("alice@acme.com")
    event["userPoolId"] = "us-east-1_OTHER000000"
    with pytest.raises(SignupRejected, match="Invalid signup"):
        handler(event, None)


def test_env_var_extra_denylist(
    monkeypatch: pytest.MonkeyPatch, _no_existing_org
) -> None:
    monkeypatch.setenv("CONSUMER_EMAIL_DENYLIST", "evil.example,banned.test")
    with pytest.raises(SignupRejected, match="work email"):
        handler(_event("user@evil.example"), None)
    with pytest.raises(SignupRejected, match="work email"):
        handler(_event("user@banned.test"), None)


def test_db_error_surfaces_generic_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A DB failure must NOT leak details to the user — generic apology."""
    mock = AsyncMock(side_effect=RuntimeError("connection refused to host xyz"))
    monkeypatch.setattr(handler_mod, "get_org_by_domain", mock)

    class _Ctx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_a):
            return False

    monkeypatch.setattr(handler_mod, "superuser_session", lambda: _Ctx())
    with pytest.raises(SignupRejected, match="try again") as excinfo:
        handler(_event("alice@acme.com"), None)
    assert "connection refused" not in str(excinfo.value)
    assert "host xyz" not in str(excinfo.value)

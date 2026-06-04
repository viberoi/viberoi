"""Unit tests for the Pre Token Generation handler."""

from __future__ import annotations

from typing import Any

from cognito_pre_token_gen.handler import handler


def _event(
    *,
    org_id: str | None = "00000000-0000-0000-0000-000000000001",
    developer_id: str | None = "00000000-0000-0000-0000-000000000101",
    role: str | None = "OrgAdmin",
    team_id: str | None = None,
) -> dict[str, Any]:
    user_attrs: dict[str, str] = {
        "sub": "11111111-2222-3333-4444-555555555555",
        "email": "alice@example.com",
    }
    if org_id is not None:
        user_attrs["custom:org_id"] = org_id
    if developer_id is not None:
        user_attrs["custom:developer_id"] = developer_id
    if role is not None:
        user_attrs["custom:role"] = role
    if team_id is not None:
        user_attrs["custom:team_id"] = team_id

    return {
        "version": "2",
        "region": "us-east-1",
        "userPoolId": "us-east-1_TEST123456",
        "userName": "alice",
        "callerContext": {"awsSdkVersion": "x", "clientId": "stub-client"},
        "triggerSource": "TokenGeneration_Authentication",
        "request": {
            "userAttributes": user_attrs,
            "scopes": ["openid", "email"],
        },
        "response": {"claimsAndScopeOverrideDetails": None},
    }


def _claims_override(result: dict[str, Any]) -> dict[str, str]:
    details = result["response"]["claimsAndScopeOverrideDetails"]
    return details["accessTokenGeneration"]["claimsToAddOrOverride"]


def test_required_claims_injected() -> None:
    result = handler(_event(), None)
    claims = _claims_override(result)
    assert claims["custom:org_id"] == "00000000-0000-0000-0000-000000000001"
    assert claims["custom:developer_id"] == "00000000-0000-0000-0000-000000000101"
    assert claims["custom:role"] == "OrgAdmin"


def test_team_id_optional_included_when_present() -> None:
    result = handler(
        _event(team_id="ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb"),
        None,
    )
    claims = _claims_override(result)
    assert claims["custom:team_id"] == "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb"


def test_team_id_omitted_when_absent() -> None:
    result = handler(_event(), None)
    claims = _claims_override(result)
    assert "custom:team_id" not in claims


def test_missing_org_id_returns_event_unchanged() -> None:
    result = handler(_event(org_id=None), None)
    # No override emitted — backend verifier will reject the token.
    assert result["response"]["claimsAndScopeOverrideDetails"] is None


def test_missing_developer_id_returns_event_unchanged() -> None:
    result = handler(_event(developer_id=None), None)
    assert result["response"]["claimsAndScopeOverrideDetails"] is None


def test_missing_role_returns_event_unchanged() -> None:
    result = handler(_event(role=None), None)
    assert result["response"]["claimsAndScopeOverrideDetails"] is None


def test_event_response_shape_initialized_when_null() -> None:
    """Cognito may send response null on first invocation. We must set it."""
    event = _event()
    event["response"] = {}  # drop the placeholder
    result = handler(event, None)
    assert "claimsAndScopeOverrideDetails" in result["response"]

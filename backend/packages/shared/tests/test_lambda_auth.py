"""Unit tests for `viberoi_shared.lambda_auth.verify`."""

from types import SimpleNamespace
from typing import Any

import pytest

from viberoi_shared.errors import Unauthorized
from viberoi_shared.lambda_auth import verify

_CTX = SimpleNamespace(aws_request_id="test-req-1")


# ── webhook ─────────────────────────────────────────────────────────────────


def _valid_apigw_v2_event() -> dict[str, Any]:
    return {
        "version": "2.0",
        "requestContext": {"http": {"method": "POST"}},
        "headers": {},
        "body": "",
    }


def test_webhook_valid_apigw_v2_event() -> None:
    verify(_valid_apigw_v2_event(), _CTX, expected_source="webhook:github")


def test_webhook_rejects_v1_event() -> None:
    event = _valid_apigw_v2_event()
    event["version"] = "1.0"
    with pytest.raises(Unauthorized):
        verify(event, _CTX, expected_source="webhook:github")


def test_webhook_rejects_get_method() -> None:
    event = _valid_apigw_v2_event()
    event["requestContext"]["http"]["method"] = "GET"
    with pytest.raises(Unauthorized):
        verify(event, _CTX, expected_source="webhook:github")


def test_webhook_rejects_empty_event() -> None:
    with pytest.raises(Unauthorized):
        verify({}, _CTX, expected_source="webhook:github")


def test_webhook_lowercase_method_accepted() -> None:
    """Some clients send lowercase methods; the spec is case-insensitive."""
    event = _valid_apigw_v2_event()
    event["requestContext"]["http"]["method"] = "post"
    verify(event, _CTX, expected_source="webhook:linear")


# ── cognito ─────────────────────────────────────────────────────────────────


def test_cognito_presignup_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_xxxxxxxxx")
    event = {
        "userPoolId": "us-east-1_xxxxxxxxx",
        "triggerSource": "PreSignUp_SignUp",
    }
    verify(event, _CTX, expected_source="cognito:presignup")


def test_cognito_presignup_wrong_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_aaaaa")
    event = {
        "userPoolId": "us-east-1_DIFFERENT",
        "triggerSource": "PreSignUp_SignUp",
    }
    with pytest.raises(Unauthorized):
        verify(event, _CTX, expected_source="cognito:presignup")


def test_cognito_presignup_wrong_trigger_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_xxxxxxxxx")
    event = {
        "userPoolId": "us-east-1_xxxxxxxxx",
        "triggerSource": "PreAuthentication_Authentication",  # wrong trigger
    }
    with pytest.raises(Unauthorized):
        verify(event, _CTX, expected_source="cognito:presignup")


def test_cognito_postconfirmation_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_xxxxxxxxx")
    event = {
        "userPoolId": "us-east-1_xxxxxxxxx",
        "triggerSource": "PostConfirmation_ConfirmSignUp",
    }
    verify(event, _CTX, expected_source="cognito:postconfirmation")


def test_cognito_missing_env_var_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A misconfigured Lambda (no env var) must reject, never accept."""
    monkeypatch.delenv("COGNITO_USER_POOL_ID", raising=False)
    event = {
        "userPoolId": "us-east-1_xxxxxxxxx",
        "triggerSource": "PreSignUp_SignUp",
    }
    with pytest.raises(Unauthorized):
        verify(event, _CTX, expected_source="cognito:presignup")


# ── eventbridge ─────────────────────────────────────────────────────────────


def test_eventbridge_valid_rule_match() -> None:
    event = {
        "source": "aws.events",
        "resources": [
            "arn:aws:events:us-east-1:123456789012:rule/kpi_snapshot_refresh"
        ],
    }
    verify(event, _CTX, expected_source="eventbridge:kpi_snapshot_refresh")


def test_eventbridge_wrong_source() -> None:
    event = {
        "source": "aws.scheduler",
        "resources": ["arn:aws:events:us-east-1:1:rule/kpi_snapshot_refresh"],
    }
    with pytest.raises(Unauthorized):
        verify(event, _CTX, expected_source="eventbridge:kpi_snapshot_refresh")


def test_eventbridge_rule_name_not_in_resources() -> None:
    event = {
        "source": "aws.events",
        "resources": ["arn:aws:events:us-east-1:1:rule/different_rule"],
    }
    with pytest.raises(Unauthorized):
        verify(event, _CTX, expected_source="eventbridge:kpi_snapshot_refresh")


def test_eventbridge_missing_rule_name() -> None:
    with pytest.raises(Unauthorized):
        verify({"source": "aws.events"}, _CTX, expected_source="eventbridge:")


# ── dispatcher ──────────────────────────────────────────────────────────────


def test_unknown_source_kind_rejected() -> None:
    with pytest.raises(Unauthorized):
        verify(_valid_apigw_v2_event(), _CTX, expected_source="alien:something")


def test_no_context_is_safe() -> None:
    """Lambda may pass None for context in some test harnesses — don't crash."""
    verify(_valid_apigw_v2_event(), None, expected_source="webhook:github")

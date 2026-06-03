"""PostConfirmation Lambda test setup."""

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TEST123456")
    # Skip the real Cognito SDK call inside _set_cognito_custom_attrs.
    monkeypatch.setenv("VIBEROI_COGNITO_SKIP_ATTR_WRITE", "1")

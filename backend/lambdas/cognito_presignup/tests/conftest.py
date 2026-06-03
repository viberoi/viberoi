"""PreSignUp Lambda test setup."""

import pytest


@pytest.fixture(autouse=True)
def _set_pool_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`lambda_auth.verify` reads COGNITO_USER_POOL_ID from os.environ."""
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TEST123456")

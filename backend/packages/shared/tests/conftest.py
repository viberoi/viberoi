"""Shared pytest fixtures and config for viberoi-shared tests.

Integration tests (marked `@pytest.mark.integration`):
  - Collection: auto-skipped if LocalStack isn't reachable.
  - Runtime: env is set so client factories hit LocalStack and the
    settings cache picks up the test config. monkeypatch restores
    everything when the test ends.

To run integration tests:  ./scripts/dev-up.ps1  then  uv run pytest -m integration
To run unit tests only:    uv run pytest  (the pyproject default excludes integration)
"""

import httpx
import pytest

_LOCALSTACK_URL = "http://localhost:4566"


def _localstack_is_up() -> bool:
    try:
        return (
            httpx.get(f"{_LOCALSTACK_URL}/_localstack/health", timeout=2).status_code
            == 200
        )
    except Exception:
        return False


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Auto-skip integration tests when LocalStack isn't running."""
    if _localstack_is_up():
        return
    skip = pytest.mark.skip(
        reason="LocalStack not running — start with ./scripts/dev-up.ps1"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _integration_env(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For integration-marked tests, point settings at LocalStack."""
    if "integration" not in request.keywords:
        return
    monkeypatch.setenv("VIBEROI_ENV", "test")
    monkeypatch.setenv("VIBEROI_AWS_REGION", "us-east-1")
    monkeypatch.setenv("VIBEROI_AWS_ENDPOINT_URL", _LOCALSTACK_URL)
    monkeypatch.setenv("VIBEROI_KMS_KEY_ID", "alias/viberoi-pii")

    from viberoi_shared.config.settings import get_settings

    get_settings.cache_clear()

"""Root pytest config — applies to every test in the workspace.

Two autouse responsibilities:

  1. Reset `get_settings()`' lru_cache + close singleton Redis client
     before and after every test. Without this, env-var changes via
     `monkeypatch` leak across tests, and the async Redis client holds
     a reference to a dead event loop.

  2. For tests marked `@pytest.mark.integration`, inject LocalStack /
     Postgres / Redis env vars via `monkeypatch` (auto-restored on
     teardown). Also auto-skip the whole integration set if LocalStack
     isn't reachable at collection time.
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


def _reset_singletons() -> None:
    """Clear in-process caches that don't survive across event loops or env changes."""
    from viberoi_shared.config.settings import get_settings

    get_settings.cache_clear()

    # The async Redis client holds a reference to the event loop it was
    # created on. pytest-asyncio uses a fresh loop per test in auto mode,
    # so a stale singleton produces "Event loop is closed" on the next test.
    # Direct null is safe — GC handles the old client; the next call to
    # get_client() builds a fresh one tied to the new event loop.
    import viberoi_shared.redis.client as redis_client_mod

    redis_client_mod._client = None

    # SQLAlchemy async engines hold the same kind of loop reference.
    import viberoi_shared.db.engine as db_engine_mod

    db_engine_mod._engine = None
    db_engine_mod._session_factory = None
    db_engine_mod._admin_engine = None
    db_engine_mod._admin_session_factory = None


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    """Runs around every test. Pairs with `_integration_env` below."""
    _reset_singletons()
    yield
    _reset_singletons()


@pytest.fixture(autouse=True)
def _integration_env(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Point settings at LocalStack for integration-marked tests."""
    if "integration" not in request.keywords:
        return
    monkeypatch.setenv("VIBEROI_ENV", "test")
    monkeypatch.setenv("VIBEROI_AWS_REGION", "us-east-1")
    monkeypatch.setenv("VIBEROI_AWS_ENDPOINT_URL", _LOCALSTACK_URL)
    monkeypatch.setenv("VIBEROI_KMS_KEY_ID", "alias/viberoi-pii")
    # Re-clear after env vars are in place so the next get_settings() picks them up.
    _reset_singletons()

"""Secrets Manager wrapper — unit tests using the dev env-var fallback.

These don't need LocalStack — the wrapper falls back to env vars when
`VIBEROI_ENV=dev|test` and Secrets Manager doesn't have the key.
"""


import pytest

from viberoi_shared import secrets


@pytest.fixture(autouse=True)
def _reset_secrets_cache():
    secrets.reset_cache()
    yield
    secrets.reset_cache()


@pytest.fixture
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBEROI_ENV", "test")


async def test_get_falls_back_to_env_var(
    monkeypatch: pytest.MonkeyPatch, _set_env: None
) -> None:
    # `viberoi/test/foo` → `VIBEROI_TEST_FOO`
    monkeypatch.setenv("VIBEROI_TEST_FOO", "the-secret-value")
    # Force AWS_ENDPOINT_URL to something that will fail so we test the fallback
    monkeypatch.setenv("VIBEROI_AWS_ENDPOINT_URL", "http://127.0.0.1:1")
    # Settings is cached; force a fresh read by clearing the cache.
    from viberoi_shared.config.settings import get_settings

    get_settings.cache_clear()
    value = await secrets.get("viberoi/test/foo")
    assert value == "the-secret-value"


async def test_get_caches_within_ttl(
    monkeypatch: pytest.MonkeyPatch, _set_env: None
) -> None:
    monkeypatch.setenv("VIBEROI_AWS_ENDPOINT_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VIBEROI_TEST_CACHED", "first")
    from viberoi_shared.config.settings import get_settings

    get_settings.cache_clear()

    first = await secrets.get("viberoi/test/cached")
    assert first == "first"

    # Change the env var; cached value should still come back.
    monkeypatch.setenv("VIBEROI_TEST_CACHED", "second")
    second = await secrets.get("viberoi/test/cached")
    assert second == "first"


async def test_get_raises_when_unavailable(
    monkeypatch: pytest.MonkeyPatch, _set_env: None
) -> None:
    monkeypatch.setenv("VIBEROI_AWS_ENDPOINT_URL", "http://127.0.0.1:1")
    monkeypatch.delenv("VIBEROI_TEST_MISSING", raising=False)
    from viberoi_shared.config.settings import get_settings

    get_settings.cache_clear()

    with pytest.raises(secrets.SecretsError):
        await secrets.get("viberoi/test/missing")


async def test_get_json_parses(
    monkeypatch: pytest.MonkeyPatch, _set_env: None
) -> None:
    monkeypatch.setenv("VIBEROI_AWS_ENDPOINT_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VIBEROI_TEST_JSON", '{"hello":"world","n":42}')
    from viberoi_shared.config.settings import get_settings

    get_settings.cache_clear()

    parsed = await secrets.get_json("viberoi/test/json")
    assert parsed == {"hello": "world", "n": 42}


async def test_get_json_rejects_bad_json(
    monkeypatch: pytest.MonkeyPatch, _set_env: None
) -> None:
    monkeypatch.setenv("VIBEROI_AWS_ENDPOINT_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VIBEROI_TEST_NOTJSON", "not json at all")
    from viberoi_shared.config.settings import get_settings

    get_settings.cache_clear()

    with pytest.raises(secrets.SecretsError):
        await secrets.get_json("viberoi/test/notjson")

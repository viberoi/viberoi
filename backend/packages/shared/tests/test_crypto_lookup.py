"""HMAC-SHA256 peppered lookup — unit tests.

Uses the dev/test env-var fallback in `viberoi_shared.secrets`, so this
test runs without LocalStack. The `VIBEROI_AWS_ENDPOINT_URL` is pointed
at an unroutable address to force the secrets module onto its env-var
fallback path.
"""

import pytest

from viberoi_shared.crypto import LookupHashError, hmac_for_lookup, reset_pepper_cache


@pytest.fixture(autouse=True)
def _reset_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set the pepper via env-var fallback so we don't need LocalStack
    # provisioning for the test env.
    monkeypatch.setenv("VIBEROI_ENV", "test")
    monkeypatch.setenv(
        "VIBEROI_TEST_LOOKUP_PEPPER",
        '{"pepper":"test-pepper-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}',
    )
    monkeypatch.setenv("VIBEROI_AWS_ENDPOINT_URL", "http://127.0.0.1:1")
    from viberoi_shared.config.settings import get_settings
    from viberoi_shared import secrets

    get_settings.cache_clear()
    secrets.reset_cache()
    reset_pepper_cache()
    yield
    reset_pepper_cache()
    secrets.reset_cache()


async def test_hmac_is_deterministic() -> None:
    a = await hmac_for_lookup("adnan@company.com")
    b = await hmac_for_lookup("adnan@company.com")
    assert a == b
    assert len(a) == 32  # SHA-256 output


async def test_hmac_normalizes_case_and_whitespace() -> None:
    a = await hmac_for_lookup("adnan@company.com")
    b = await hmac_for_lookup("  ADNAN@COMPANY.COM  ")
    assert a == b


async def test_hmac_differs_for_different_inputs() -> None:
    a = await hmac_for_lookup("a@example.com")
    b = await hmac_for_lookup("b@example.com")
    assert a != b


async def test_hmac_rejects_empty() -> None:
    with pytest.raises(LookupHashError):
        await hmac_for_lookup("")


async def test_hmac_rejects_weak_pepper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEROI_TEST_LOOKUP_PEPPER", '{"pepper":"too-short"}')
    from viberoi_shared import secrets

    secrets.reset_cache()
    reset_pepper_cache()
    with pytest.raises(LookupHashError):
        await hmac_for_lookup("anything@x.com")

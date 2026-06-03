"""Cognito JWT verification — unit tests against a synthetic JWKS.

We mint tokens with a test RSA keypair and patch the verifier's JWKS
resolver to return the matching public key. No network, no real
Cognito.
"""

from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from viberoi_shared.cognito import (
    CognitoClaims,
    CognitoVerificationError,
    reset_jwks_cache,
    verify as verify_mod,
    verify_jwt,
)
from viberoi_shared.config import get_settings

KID = "test-kid-1"


# ── keypair + JWKS fixtures ─────────────────────────────────────────────────


@pytest.fixture(scope="module")
def _keypair() -> tuple[str, Any]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return private_pem, key.public_key()


@pytest.fixture(autouse=True)
def _patch_jwks(monkeypatch: pytest.MonkeyPatch, _keypair) -> None:
    """Replace the PyJWKClient lookup with a direct return of our test pubkey."""
    _, public_key = _keypair

    class _FakeSigningKey:
        def __init__(self, k: Any) -> None:
            self.key = k

    class _FakeClient:
        def __init__(self, *_a, **_kw) -> None:
            pass

        def get_signing_key_from_jwt(self, _token: str) -> _FakeSigningKey:
            return _FakeSigningKey(public_key)

    monkeypatch.setattr(verify_mod, "PyJWKClient", _FakeClient)
    reset_jwks_cache()


# ── token minting helper ────────────────────────────────────────────────────


def _mint(
    private_pem: str,
    *,
    overrides: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    drop: set[str] | None = None,
) -> str:
    settings = get_settings()
    iss = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}"
    )
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": "11111111-2222-3333-4444-555555555555",
        "iss": iss,
        "client_id": settings.cognito_app_client_id,
        "token_use": "access",
        "iat": now,
        "exp": now + 3600,
        "custom:developer_id": "99999999-8888-7777-6666-555555555555",
        "custom:org_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "custom:role": "OrgAdmin",
        "custom:team_id": None,
        "email": "alice@example.com",
    }
    if overrides:
        payload.update(overrides)
    if drop:
        for k in drop:
            payload.pop(k, None)
    full_headers = {"kid": KID, **(headers or {})}
    return jwt.encode(payload, private_pem, algorithm="RS256", headers=full_headers)


# ── happy path ──────────────────────────────────────────────────────────────


async def test_verify_valid_token_returns_claims(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(private_pem)
    claims = await verify_jwt(token)
    assert isinstance(claims, CognitoClaims)
    assert claims.sub == "11111111-2222-3333-4444-555555555555"
    assert str(claims.developer_id) == "99999999-8888-7777-6666-555555555555"
    assert str(claims.org_id) == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert claims.role.value == "OrgAdmin"
    assert claims.team_id is None


async def test_verify_with_team_id_set(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(
        private_pem,
        overrides={
            "custom:team_id": "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
            "custom:role": "TeamLead",
        },
    )
    claims = await verify_jwt(token)
    assert claims.role.value == "TeamLead"
    assert str(claims.team_id) == "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb"


# ── rejection paths ─────────────────────────────────────────────────────────


async def test_expired_token_rejected(_keypair) -> None:
    private_pem, _ = _keypair
    now = int(time.time())
    token = _mint(
        private_pem, overrides={"iat": now - 7200, "exp": now - 3600}
    )
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(token)


async def test_wrong_issuer_rejected(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(
        private_pem,
        overrides={"iss": "https://cognito-idp.eu-west-1.amazonaws.com/eu_FAKE"},
    )
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(token)


async def test_wrong_client_id_rejected(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(private_pem, overrides={"client_id": "some-other-client"})
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(token)


async def test_id_token_rejected_as_access_token(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(private_pem, overrides={"token_use": "id"})
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(token)


async def test_tampered_signature_rejected(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(private_pem)
    parts = token.split(".")
    parts[2] = "AAAAAA"  # garbage signature
    bad = ".".join(parts)
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(bad)


async def test_missing_org_id_rejected(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(private_pem, drop={"custom:org_id"})
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(token)


async def test_missing_developer_id_rejected(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(private_pem, drop={"custom:developer_id"})
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(token)


async def test_invalid_role_rejected(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(private_pem, overrides={"custom:role": "GodMode"})
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(token)


async def test_missing_token_use_rejected(_keypair) -> None:
    private_pem, _ = _keypair
    token = _mint(private_pem, drop={"token_use"})
    with pytest.raises(CognitoVerificationError):
        await verify_jwt(token)

"""KMS envelope encryption — integration tests (requires LocalStack).

Run with `pytest -m integration` (excluded by default in pyproject.toml).
LocalStack must be up via `./scripts/dev-up.ps1` (or `.sh`).
"""

import pytest

from viberoi_shared.crypto import (
    EncryptedField,
    EncryptionError,
    decrypt_pii,
    encrypt_pii,
)

pytestmark = pytest.mark.integration


async def test_encrypt_decrypt_round_trip() -> None:
    plaintext = "adnan@company.com"
    ctx = "org:00000000-0000-0000-0000-000000000001:field:email"

    field = await encrypt_pii(plaintext, context=ctx)
    assert isinstance(field, EncryptedField)
    assert field.ciphertext != plaintext.encode("utf-8")
    assert len(field.iv) == 12
    assert field.key_version >= 1

    recovered = await decrypt_pii(field, context=ctx)
    assert recovered == plaintext


async def test_encrypt_produces_different_ciphertext_for_same_input() -> None:
    """Fresh DEK + fresh IV per call — ciphertexts must differ."""
    ctx = "org:test:field:email"
    a = await encrypt_pii("same@email.com", context=ctx)
    b = await encrypt_pii("same@email.com", context=ctx)
    assert a.ciphertext != b.ciphertext
    assert a.iv != b.iv


async def test_decrypt_with_wrong_context_fails() -> None:
    field = await encrypt_pii("email@a.com", context="org:A:field:email")
    with pytest.raises(EncryptionError):
        await decrypt_pii(field, context="org:B:field:email")


async def test_decrypt_with_tampered_ciphertext_fails() -> None:
    ctx = "org:test:field:email"
    field = await encrypt_pii("clean@email.com", context=ctx)
    # Flip a byte in the AES-GCM ciphertext portion (past the DEK header)
    tampered = bytearray(field.ciphertext)
    tampered[-1] ^= 0x01
    bad = EncryptedField(
        ciphertext=bytes(tampered), key_version=field.key_version, iv=field.iv
    )
    with pytest.raises(EncryptionError):
        await decrypt_pii(bad, context=ctx)


async def test_decrypt_with_tampered_iv_fails() -> None:
    ctx = "org:test:field:email"
    field = await encrypt_pii("clean@email.com", context=ctx)
    bad_iv = bytearray(field.iv)
    bad_iv[0] ^= 0x01
    bad = EncryptedField(
        ciphertext=field.ciphertext, key_version=field.key_version, iv=bytes(bad_iv)
    )
    with pytest.raises(EncryptionError):
        await decrypt_pii(bad, context=ctx)


async def test_encrypt_rejects_empty_string() -> None:
    with pytest.raises(EncryptionError):
        await encrypt_pii("", context="org:test:field:email")


async def test_encrypt_round_trip_unicode() -> None:
    """Non-ASCII PII must survive the round trip."""
    ctx = "org:test:field:name"
    plaintext = "André François 中文 🎉"
    field = await encrypt_pii(plaintext, context=ctx)
    recovered = await decrypt_pii(field, context=ctx)
    assert recovered == plaintext

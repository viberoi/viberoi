"""Argon2id hash + verify round-trip."""

import pytest

from viberoi_shared.crypto import hash_secret, needs_rehash, verify_secret
from viberoi_shared.crypto.hash import HashError


def test_hash_verify_round_trip():
    h = hash_secret("super-secret-token")
    assert h.startswith("$argon2id$")
    assert verify_secret("super-secret-token", h)
    assert not verify_secret("wrong-token", h)


def test_hash_produces_different_outputs_for_same_input():
    a = hash_secret("same-input")
    b = hash_secret("same-input")
    assert a != b, "different salts must produce different hashes"
    assert verify_secret("same-input", a)
    assert verify_secret("same-input", b)


def test_verify_empty_inputs_returns_false():
    h = hash_secret("not-empty")
    assert not verify_secret("", h)
    assert not verify_secret("not-empty", "")


def test_hash_empty_raises():
    with pytest.raises(HashError):
        hash_secret("")


def test_verify_invalid_hash_returns_false():
    assert not verify_secret("token", "not-a-real-argon2-hash")


def test_needs_rehash_for_invalid_hash():
    assert needs_rehash("garbage")

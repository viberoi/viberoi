"""Argon2id hashing for secrets we only verify (never decrypt).

Used for `org_token`, webhook signing secrets, and any token where we
compare submitted-vs-stored without ever needing the original back.

Parameters come from `SharedSettings` (defaults match OWASP 2024 guidance).
"""

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from viberoi_shared.config import get_settings
from viberoi_shared.errors.types import VibeRoiError


class HashError(VibeRoiError):
    code = "hash_error"
    safe_message = "Failed to hash secret."


def _hasher() -> PasswordHasher:
    s = get_settings()
    return PasswordHasher(
        time_cost=s.argon2_time_cost,
        memory_cost=s.argon2_memory_cost_kib,
        parallelism=s.argon2_parallelism,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )


def hash_secret(secret: str) -> str:
    """Hash a secret with Argon2id. Returns a self-describing hash string."""
    if not secret:
        raise HashError("Cannot hash empty secret.")
    return _hasher().hash(secret)


def verify_secret(secret: str, hashed: str) -> bool:
    """Verify a secret against a stored hash. Returns False on any mismatch."""
    if not secret or not hashed:
        return False
    try:
        return _hasher().verify(hashed, secret)
    except VerifyMismatchError:
        return False
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if the hash was created with different params (re-hash on next verify)."""
    try:
        return _hasher().check_needs_rehash(hashed)
    except InvalidHashError:
        return True

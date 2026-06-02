"""HMAC-SHA256 for searchable encrypted PII columns.

Encrypted columns can't be queried directly. Pattern: alongside each
encrypted column, store a `<field>_hash` column = `HMAC-SHA256(value, pepper)`.
The hash is deterministic — same plaintext always produces the same hash —
so an indexed lookup works without ever decrypting.

The pepper is fetched from Secrets Manager (`viberoi/<env>/lookup_pepper`)
and is shared across the entire app. Rotation is rare; when rotated, all
existing `*_hash` values must be recomputed (background job).

Normalization: values are stripped + lowercased before hashing so
`"adnan@company.com"`, `"  ADNAN@COMPANY.COM "` produce the same hash.
"""

import hashlib
import hmac

from viberoi_shared.config import Env, get_settings
from viberoi_shared.errors.types import VibeRoiError
from viberoi_shared.secrets import get_json


class LookupHashError(VibeRoiError):
    code = "lookup_hash_error"
    safe_message = "Failed to compute lookup hash."


def _pepper_key() -> str:
    env = get_settings().env
    return f"viberoi/{env.value}/lookup_pepper"


_pepper_cache: bytes | None = None


async def _get_pepper() -> bytes:
    global _pepper_cache
    if _pepper_cache is None:
        try:
            blob = await get_json(_pepper_key())
            pepper = blob.get("pepper")
            if not isinstance(pepper, str) or len(pepper) < 32:
                raise LookupHashError(
                    "Pepper is missing or shorter than 32 chars."
                )
            _pepper_cache = pepper.encode("utf-8")
        except LookupHashError:
            raise
        except Exception as e:
            raise LookupHashError("Could not fetch lookup pepper") from e
    return _pepper_cache


async def hmac_for_lookup(value: str) -> bytes:
    """Deterministic HMAC-SHA256 of `value` for `*_hash` column lookup."""
    if not value:
        raise LookupHashError("Cannot hash empty value")
    normalized = value.strip().lower().encode("utf-8")
    pepper = await _get_pepper()
    return hmac.new(pepper, normalized, hashlib.sha256).digest()


def reset_pepper_cache() -> None:
    """For tests + after pepper rotation."""
    global _pepper_cache
    _pepper_cache = None


def _is_dev_or_test() -> bool:
    return get_settings().env in (Env.DEV, Env.TEST)

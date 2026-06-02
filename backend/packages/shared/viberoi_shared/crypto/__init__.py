"""Argon2id hashing + KMS envelope encryption (AES-256-GCM) + peppered HMAC lookup.

Argon2id (one-way, verify-only):
  `hash_secret(secret)` / `verify_secret(secret, hash)` / `needs_rehash(hash)`
  — for `org_token`, webhook signing keys, anything we only verify.

KMS envelope (recoverable, AAD-bound):
  `encrypt_pii(value, context=...)` -> EncryptedField
  `decrypt_pii(field, context=...)` -> str
  Each encrypted column stores `(ciphertext, key_version, iv)`.

Searchable PII (deterministic):
  `hmac_for_lookup(value)` — HMAC-SHA256 with a peppered key from
  Secrets Manager. Stored in the `*_hash` lookup column.

This is the ONLY module allowed to import KMS / `cryptography.hazmat`.
"""

from viberoi_shared.crypto.envelope import (
    CURRENT_KEY_VERSION,
    EncryptedField,
    EncryptionError,
    decrypt_pii,
    encrypt_pii,
)
from viberoi_shared.crypto.hash import hash_secret, needs_rehash, verify_secret
from viberoi_shared.crypto.lookup import (
    LookupHashError,
    hmac_for_lookup,
    reset_pepper_cache,
)

__all__ = [
    "CURRENT_KEY_VERSION",
    "EncryptedField",
    "EncryptionError",
    "LookupHashError",
    "decrypt_pii",
    "encrypt_pii",
    "hash_secret",
    "hmac_for_lookup",
    "needs_rehash",
    "reset_pepper_cache",
    "verify_secret",
]

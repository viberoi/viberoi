"""Argon2id hashing + KMS envelope encryption (AES-256-GCM).

Argon2id (implemented): `hash_secret(secret)` / `verify_secret(secret, hash)` / `needs_rehash(hash)`
  — for `org_token`, webhook signing keys, anything we only verify.

KMS envelope (lands with LocalStack in Slice 5):
  `encrypt_pii(value, context)` / `decrypt_pii(ct, ver, iv, context)`
  — for `developers.email`, `orgs.billing_email`, OAuth tokens, webhook URLs.
  Each encrypted column stores `(ciphertext, key_version, iv)`.

Searchable PII (lands with LocalStack in Slice 5):
  `hmac_for_lookup(value)` — deterministic HMAC-SHA256 with a peppered
  key from Secrets Manager, used for the `*_hash` lookup column.

This is the ONLY module allowed to import boto3 KMS or `cryptography.hazmat`.
"""

from viberoi_shared.crypto.hash import hash_secret, needs_rehash, verify_secret

__all__ = ["hash_secret", "needs_rehash", "verify_secret"]

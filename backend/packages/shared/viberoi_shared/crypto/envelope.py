"""KMS envelope encryption for PII at rest.

Pattern (per `.claude/rules/security.md`):
  1. `KMS.GenerateDataKey(AES_256)` → `(plaintext_dek, encrypted_dek)`
  2. Generate fresh 12-byte nonce
  3. AES-256-GCM encrypt plaintext with `plaintext_dek`, AAD = `context`
  4. Store packed `[u32 dek_len][encrypted_dek][aes-gcm ciphertext]`
     in `<field>_ciphertext`, plus `<field>_key_version` and `<field>_iv`

`context` is the AAD — it binds the ciphertext to its location, so
copying ciphertext to a different row/field can't decrypt. Typically:
    f"org:{org_id}:field:{name}"

Rotation: KMS rotates the CMK annually + on-demand. Reads work across
all key versions automatically (KMS knows). `key_version` here is OUR
counter — bump it when WE want to force re-encryption of old rows.
"""

import os
import struct
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from viberoi_shared.aws import kms_client
from viberoi_shared.config import get_settings
from viberoi_shared.errors.types import VibeRoiError

# Bump when introducing a structural change to the packed format or when
# forcing a full re-encryption pass. Reads dispatch on this.
CURRENT_KEY_VERSION = 1


class EncryptionError(VibeRoiError):
    code = "encryption_error"
    safe_message = "Failed to encrypt or decrypt PII."


@dataclass(frozen=True)
class EncryptedField:
    """The persisted shape for an encrypted PII column.

    Stored as three DB columns: `<field>_ciphertext` (BYTEA),
    `<field>_key_version` (SMALLINT), `<field>_iv` (BYTEA).
    """

    ciphertext: bytes
    key_version: int
    iv: bytes


async def encrypt_pii(plaintext: str, *, context: str) -> EncryptedField:
    """Encrypt a PII string with KMS envelope + AES-256-GCM.

    `context` must be reconstructible at decrypt time — typically
    derived from the row's identity (e.g., `f"org:{org_id}:field:email"`).
    """
    if plaintext == "":
        raise EncryptionError("Cannot encrypt empty string.")
    s = get_settings()
    aad = context.encode("utf-8")
    plaintext_bytes = plaintext.encode("utf-8")

    async with kms_client() as kms:
        try:
            resp = await kms.generate_data_key(
                KeyId=s.kms_key_id,
                KeySpec="AES_256",
                EncryptionContext={"context": context},
            )
        except Exception as e:
            raise EncryptionError("KMS.GenerateDataKey failed") from e

    plaintext_dek: bytes = resp["Plaintext"]
    encrypted_dek: bytes = resp["CiphertextBlob"]

    iv = os.urandom(12)
    aesgcm = AESGCM(plaintext_dek)
    aes_ciphertext = aesgcm.encrypt(iv, plaintext_bytes, aad)

    # Pack: 4-byte big-endian length prefix + encrypted_dek + aes_ciphertext.
    # Simple, version-tolerant; CURRENT_KEY_VERSION tracks structural changes.
    packed = struct.pack(">I", len(encrypted_dek)) + encrypted_dek + aes_ciphertext

    return EncryptedField(
        ciphertext=packed,
        key_version=CURRENT_KEY_VERSION,
        iv=iv,
    )


async def decrypt_pii(field: EncryptedField, *, context: str) -> str:
    """Decrypt a previously-encrypted PII string.

    Raises `EncryptionError` if KMS rejects the encrypted DEK, the
    AAD context doesn't match, or AES-GCM auth tag verification fails.
    """
    aad = context.encode("utf-8")

    # Unpack length prefix
    if len(field.ciphertext) < 4:
        raise EncryptionError("Ciphertext too short to unpack.")
    dek_len = struct.unpack(">I", field.ciphertext[:4])[0]
    if dek_len <= 0 or 4 + dek_len > len(field.ciphertext):
        raise EncryptionError("Ciphertext has invalid DEK length.")
    encrypted_dek = field.ciphertext[4 : 4 + dek_len]
    aes_ciphertext = field.ciphertext[4 + dek_len :]

    async with kms_client() as kms:
        try:
            resp = await kms.decrypt(
                CiphertextBlob=encrypted_dek,
                EncryptionContext={"context": context},
            )
        except Exception as e:
            raise EncryptionError(
                "KMS.Decrypt failed (key rotation or context mismatch?)"
            ) from e

    plaintext_dek: bytes = resp["Plaintext"]
    aesgcm = AESGCM(plaintext_dek)

    try:
        plaintext_bytes = aesgcm.decrypt(field.iv, aes_ciphertext, aad)
    except InvalidTag as e:
        raise EncryptionError("AES-GCM auth tag verification failed.") from e

    return plaintext_bytes.decode("utf-8")

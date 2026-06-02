"""S3 raw-landing helpers for the agent → backend session pipeline.

Layout:
    s3://viberoi-org-data/orgs/{org_id}/sessions/{YYYY-MM-DD}/{session_id}.json.gz

Key shape is deterministic so the S3-event → SQS bridge can parse the
org_id from the key without metadata lookup.

PUT enforces SSE — explicit safety against accidentally landing raw
agent payloads in unencrypted storage. (The bucket also has bucket-level
default SSE per `scripts/localstack-init.sh` / Terraform, so this is
defense in depth.)
"""

from datetime import datetime
from uuid import UUID

from viberoi_shared.aws import s3_client
from viberoi_shared.errors.types import VibeRoiError

RAW_BUCKET = "viberoi-org-data"


class S3Error(VibeRoiError):
    code = "s3_error"
    safe_message = "S3 operation failed."


def raw_landing_key(org_id: UUID | str, session_id: str, captured_at: datetime) -> str:
    """Canonical S3 key for a raw session payload."""
    date = captured_at.strftime("%Y-%m-%d")
    return f"orgs/{org_id}/sessions/{date}/{session_id}.json.gz"


async def put_raw_session(
    *,
    org_id: UUID | str,
    session_id: str,
    captured_at: datetime,
    body: bytes,
) -> str:
    """PUT a gzipped session payload to raw landing. Returns the S3 key.

    `body` is gzipped JSON bytes — the agent gzips before POST, the
    Ingest service writes the gzipped bytes through unchanged. We never
    decompress at this layer.
    """
    key = raw_landing_key(org_id, session_id, captured_at)
    async with s3_client() as s3:
        try:
            await s3.put_object(
                Bucket=RAW_BUCKET,
                Key=key,
                Body=body,
                ContentType="application/json",
                ContentEncoding="gzip",
                ServerSideEncryption="AES256",
            )
        except Exception as e:
            raise S3Error(f"Failed to PUT s3://{RAW_BUCKET}/{key}") from e
    return key


async def get_raw_session(key: str) -> bytes:
    """GET a raw session payload. Used by the Worker after S3 event delivery."""
    async with s3_client() as s3:
        try:
            resp = await s3.get_object(Bucket=RAW_BUCKET, Key=key)
            async with resp["Body"] as stream:
                return await stream.read()
        except Exception as e:
            raise S3Error(f"Failed to GET s3://{RAW_BUCKET}/{key}") from e


async def head_raw_session(key: str) -> bool:
    """True if the object exists; used by idempotency checks."""
    async with s3_client() as s3:
        try:
            await s3.head_object(Bucket=RAW_BUCKET, Key=key)
        except Exception:
            return False
    return True

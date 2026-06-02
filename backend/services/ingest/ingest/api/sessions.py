"""Session ingest endpoints (Slice 1 stub).

Final shape (Slice 3):
  1. Verify HMAC signature on raw body using `org_token` Argon2id hash
  2. Gunzip payload
  3. Validate against `viberoi_shared.types.Session`
  4. Write raw bytes to S3 `viberoi-org-data/orgs/{org_id}/sessions/{date}/{session}.json.gz`
  5. Return 202 immediately (S3 event → SQS `session_ingest` → Worker)

Slice 1 validates the Pydantic shape and returns 202 — proves the
wiring + OpenAPI schema work end-to-end. No storage, no auth yet.
"""

from fastapi import APIRouter, status

from ingest.schema.requests import IngestRequest
from ingest.schema.responses import IngestResponse
from viberoi_shared.errors import ValidationFailed
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

_BATCH_LIMIT = 100


@router.post(
    "/session",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_session(payload: IngestRequest) -> IngestResponse:
    """Accept a single session for async processing."""
    logger.info(
        "ingest_session_received",
        session_id=payload.session.session_id,
        tool=payload.session.tool.name.value,
        org_id=payload.session.org_id,
    )
    return IngestResponse(
        accepted=1,
        rejected=0,
        message="accepted (Slice 1 stub — S3 write lands in Slice 3 final)",
    )


@router.post(
    "/sessions",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_sessions_batch(payload: list[IngestRequest]) -> IngestResponse:
    """Accept a batch of sessions (up to 100)."""
    if len(payload) > _BATCH_LIMIT:
        raise ValidationFailed(
            f"Batch too large: {len(payload)} > {_BATCH_LIMIT}",
            details={"batch_size": len(payload), "limit": _BATCH_LIMIT},
        )
    logger.info("ingest_batch_received", count=len(payload))
    return IngestResponse(
        accepted=len(payload),
        rejected=0,
        message="accepted (Slice 1 stub)",
    )

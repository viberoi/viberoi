"""Session ingest endpoints — Slice 3 real implementation.

Flow:
  1. Bearer auth (via `authenticate` dependency) → AuthContext.
  2. Validate body's `org_id` and `developer_id` match the auth context
     (prevent cross-tenant push using stolen creds for a different dev).
  3. Gzip + PUT to S3 raw landing (via `store.land_session`).
  4. Return 202. The S3 event → SQS bridge fans out to the Worker.
"""

from fastapi import APIRouter, status

from ingest.app.auth import AuthRequired
from ingest.app.store import land_session
from ingest.schema.responses import IngestResponse
from viberoi_shared.errors import Forbidden, ValidationFailed
from viberoi_shared.logging import get_logger
from viberoi_shared.types import Session

logger = get_logger(__name__)

router = APIRouter()

_BATCH_LIMIT = 100


def _assert_session_matches_auth(session: Session, ctx: AuthRequired) -> None:
    """Reject payloads whose ids don't match the authenticated context."""
    if session.org_id != str(ctx.org_id):
        raise Forbidden("Session org_id does not match authenticated org.")
    if session.developer_id != str(ctx.developer_id):
        raise Forbidden("Session developer_id does not match authenticated developer.")


@router.post(
    "/session",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_session(session: Session, ctx: AuthRequired) -> IngestResponse:
    """Accept a single session for async processing."""
    _assert_session_matches_auth(session, ctx)
    key = await land_session(session)
    logger.info("ingest_session_accepted", session_id=session.session_id, s3_key=key)
    return IngestResponse(accepted=1, rejected=0, message="landed in raw bucket")


@router.post(
    "/sessions",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_sessions_batch(
    sessions: list[Session], ctx: AuthRequired
) -> IngestResponse:
    """Accept a batch of sessions (up to 100).

    All sessions in the batch must belong to the same authenticated
    `(org, developer)` — agents only push their own.
    """
    if len(sessions) > _BATCH_LIMIT:
        raise ValidationFailed(
            f"Batch too large: {len(sessions)} > {_BATCH_LIMIT}",
            details={"batch_size": len(sessions), "limit": _BATCH_LIMIT},
        )
    for session in sessions:
        _assert_session_matches_auth(session, ctx)

    keys: list[str] = []
    for session in sessions:
        keys.append(await land_session(session))

    logger.info("ingest_batch_accepted", count=len(sessions))
    return IngestResponse(
        accepted=len(sessions),
        rejected=0,
        message=f"landed {len(keys)} sessions in raw bucket",
    )

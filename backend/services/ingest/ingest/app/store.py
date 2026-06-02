"""Session storage orchestration.

Single responsibility: take an authenticated, validated Session, gzip
the JSON, PUT to S3 raw landing. The S3 bucket has an event notification
configured to push to SQS `session_ingest`, where the Worker picks up.

Idempotency is enforced at the DB layer (sessions UNIQUE(org_id, session_id)),
so duplicate S3 PUTs are safe — the Worker will upsert the same row twice
with no observable effect.
"""

import gzip

import orjson

from viberoi_shared.logging import get_logger
from viberoi_shared.s3 import put_raw_session
from viberoi_shared.types import Session

logger = get_logger(__name__)


async def land_session(session: Session) -> str:
    """Serialize → gzip → PUT to S3. Returns the S3 key."""
    body = orjson.dumps(session.model_dump(mode="json"))
    gzipped = gzip.compress(body)

    key = await put_raw_session(
        org_id=session.org_id,
        session_id=session.session_id,
        captured_at=session.meta.captured_at,
        body=gzipped,
    )

    logger.info(
        "session_landed",
        s3_key=key,
        session_id=session.session_id,
        gzipped_bytes=len(gzipped),
    )
    return key

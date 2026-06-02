"""Process one S3 event record: GET raw → validate → attribute → upsert → counters."""

import gzip
from uuid import UUID

import orjson

from viberoi_shared.db import org_scoped_session
from viberoi_shared.logging import bind_request_context, get_logger
from viberoi_shared.redis import incr_cost_usd, incr_session_count
from viberoi_shared.s3 import get_raw_session
from viberoi_shared.sessions import upsert
from viberoi_shared.types import Session

from worker.app.attribution import attribute
from worker.schema.events import S3EventRecord

logger = get_logger(__name__)


async def process_s3_event(record: S3EventRecord) -> None:
    """Fetch the S3 object, parse + validate, attribute, upsert, update counters.

    Idempotent: `sessions.upsert` uses `ON CONFLICT DO UPDATE` keyed on
    `(org_id, session_id)`, so duplicate S3 events safely no-op the DB.

    Counters are NOT idempotent on retry — if processing fails after
    counter increment but before SQS ack, the next attempt will
    double-increment. Acceptable for V1 (counters are eventually
    reconciled from the Postgres source of truth via the hourly KPI
    snapshot cron, Slice 6).
    """
    key = record.s3.object.key
    bind_request_context(request_id=f"s3:{key}")

    raw_bytes = await get_raw_session(key)
    decompressed = gzip.decompress(raw_bytes)
    payload = orjson.loads(decompressed)
    session = Session.model_validate(payload)

    org_uuid = UUID(session.org_id)
    developer_uuid = UUID(session.developer_id)

    # Worker is the source of truth for attribution; agent's value is advisory.
    session = session.model_copy(update={"attribution": attribute(session)})

    async with org_scoped_session(org_uuid) as db:
        row_id = await upsert(
            db, session, developer_uuid=developer_uuid, org_uuid=org_uuid
        )

    # Live KPI counters for the dashboard. Reconciled from Postgres
    # hourly via the snapshot cron (Slice 6).
    await incr_session_count(org_uuid)
    await incr_cost_usd(org_uuid, session.tokens.total_cost_usd)

    logger.info(
        "session_processed",
        session_id=session.session_id,
        row_id=str(row_id),
        ticket_id=session.attribution.ticket_id,
        confidence=float(session.attribution.confidence),
        cost_usd=float(session.tokens.total_cost_usd),
    )

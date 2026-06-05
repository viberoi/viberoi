"""Process one S3 event record: GET raw → validate → attribute → upsert → counters."""

import gzip
from uuid import UUID

import orjson
from sqlalchemy import text

from viberoi_shared.db import org_scoped_session
from viberoi_shared.logging import bind_request_context, get_logger
from viberoi_shared.pricing import compute_cost
from viberoi_shared.redis import incr_cost_usd, incr_session_count
from viberoi_shared.s3 import get_raw_session
from viberoi_shared.sessions import upsert
from viberoi_shared.types import Session

from worker.app.attribution import attribute, enrich_with_db_signals
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
    # Signal 1 (branch) is session-only; Signals 2 + 5 run inside the
    # org-scoped DB block below so they can read ticket.pr_file_paths
    # + ticket.title (populated by the GitHub webhook handler).
    session = session.model_copy(update={"attribution": attribute(session)})

    # Same for cost — agent sends 0 by design; reconcile here against the
    # current rate table so dashboards reflect today's prices even if old
    # sessions are reprocessed.
    cost, estimated = compute_cost(
        model=session.tool.model,
        input_tokens=session.tokens.input,
        output_tokens=session.tokens.output,
        cache_read_tokens=session.tokens.cache_read,
        cache_write_tokens=session.tokens.cache_write,
        pricing_type=session.tool.pricing_model.type.value,
    )
    session = session.model_copy(
        update={
            "tokens": session.tokens.model_copy(
                update={"total_cost_usd": cost, "is_estimated": estimated}
            ),
        }
    )

    async with org_scoped_session(org_uuid) as db:
        # Enrich Signal 1 with Signals 2 + 5 if the ticket row already
        # exists (webhook ran first). Otherwise Signal 1 stands alone;
        # the every-5-min backfill cron re-attributes once the PR
        # webhook arrives.
        enriched = await enrich_with_db_signals(session.attribution, session, db)
        session = session.model_copy(update={"attribution": enriched})

        row_id = await upsert(
            db, session, developer_uuid=developer_uuid, org_uuid=org_uuid
        )
        # On first push from this developer, persist their machine
        # fingerprint so the active-device meter has a value. Only
        # writes when the column is still NULL — switching machines is
        # a separate concern (a future "devices" join table will track
        # the full set).
        if session.machine_id:
            try:
                fingerprint = bytes.fromhex(session.machine_id)
                await db.execute(
                    text(
                        "UPDATE developers SET machine_id_hash = :h "
                        "WHERE id = :id AND machine_id_hash IS NULL"
                    ),
                    {"h": fingerprint, "id": str(developer_uuid)},
                )
            except ValueError:
                # Agent sent a non-hex machine_id — log and continue.
                logger.warning(
                    "machine_id_not_hex",
                    developer_id=str(developer_uuid),
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

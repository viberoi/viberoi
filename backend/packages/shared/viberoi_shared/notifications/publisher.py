"""`enqueue()` — the ONLY way services emit a notification.

Publishes a typed envelope to SQS `notification_jobs`. The Notification
Service consumes the queue, looks up the channel config, renders the
template, and delivers.

Services NEVER call Slack/Teams/SES directly. If you find yourself
importing httpx in a non-Notification service to POST a webhook, the
rule was broken — refactor to enqueue a template.

The envelope is the contract. Adding a field is a non-breaking change;
renaming or removing one needs a coordinated rollout.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from viberoi_shared.logging import get_logger
from viberoi_shared.sqs import publish as sqs_publish

logger = get_logger(__name__)

QUEUE_NAME = "notification_jobs"


class NotificationEnvelope(BaseModel):
    """Wire format on `notification_jobs`.

    `payload` is template-specific — the consumer's template registry
    validates per-template shape. Kept as `dict` here so the queue
    contract doesn't fan out.
    """

    model_config = ConfigDict(extra="forbid")

    org_id: UUID
    channel: str  # slack | teams | email
    template: str  # registry key — e.g. "integration_revoked"
    payload: dict[str, Any] = Field(default_factory=dict)
    # Optional dedup key — if two calls arrive with the same key inside
    # the SQS dedup window (FIFO only), the second is silently dropped.
    # On standard queues this is logged but doesn't affect delivery.
    dedup_key: str | None = None
    # Trace id for cross-service correlation (enqueue → consume → deliver).
    trace_id: UUID


async def enqueue(
    *,
    org_id: UUID,
    channel: str,
    template: str,
    payload: dict[str, Any] | None = None,
    dedup_key: str | None = None,
) -> UUID:
    """Publish a notification job. Returns the trace_id.

    The trace_id lets the caller correlate later — it's logged here and
    again by the consumer when the message is processed.
    """
    trace_id = uuid4()
    envelope = NotificationEnvelope(
        org_id=org_id,
        channel=channel,
        template=template,
        payload=payload or {},
        dedup_key=dedup_key,
        trace_id=trace_id,
    )
    # Namespace the SQS-level dedup id by org_id so two tenants can't
    # collide on a shared key (e.g. "integration_revoked:github"). On
    # standard queues SQS ignores deduplication_id; on FIFO queues
    # without the prefix, a tenant could suppress another tenant's
    # security-relevant alerts.
    scoped_dedup: str | None = None
    if dedup_key is not None:
        scoped_dedup = f"{org_id}:{dedup_key}"
    await sqs_publish(
        QUEUE_NAME,
        envelope.model_dump(mode="json"),
        deduplication_id=scoped_dedup,
    )
    logger.info(
        "notification_enqueued",
        org_id=str(org_id),
        channel=channel,
        template=template,
        trace_id=str(trace_id),
    )
    return trace_id

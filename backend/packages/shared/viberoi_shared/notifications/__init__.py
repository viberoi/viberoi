"""Notification enqueue + per-org channel storage.

Services NEVER call Slack/Teams/SES directly. They call
`enqueue(org_id, channel, template, payload, dedup_key=None)` which
writes a typed `NotificationEnvelope` to SQS `notification_jobs`. The
Notification Service is the only consumer.

Per-org channel config (KMS-encrypted webhook URLs) lives in
`notification_channels`. The consumer reads + decrypts on demand;
nothing else in the codebase does.
"""

from viberoi_shared.notifications.guards import assert_safe_slack_webhook_url
from viberoi_shared.notifications.models import NotificationChannel
from viberoi_shared.notifications.publisher import (
    QUEUE_NAME,
    NotificationEnvelope,
    enqueue,
)
from viberoi_shared.notifications.repository import (
    disable_channel,
    get_channel_for_org,
    get_channel_record,
    upsert_channel,
)

__all__ = [
    "QUEUE_NAME",
    "NotificationChannel",
    "NotificationEnvelope",
    "assert_safe_slack_webhook_url",
    "disable_channel",
    "enqueue",
    "get_channel_for_org",
    "get_channel_record",
    "upsert_channel",
]

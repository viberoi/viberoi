"""notification_channels

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-03

Per-org delivery channels for the Notification service. One row per
(org, channel), where `channel` is the wire-format name: `slack` for
V1; `teams` / `email` follow in V2.

For Slack/Teams: `webhook_url_*` columns hold the KMS-encrypted
webhook URL (envelope shape — ciphertext + key_version + iv). The
Notification service decrypts on demand inside the consumer; URLs
never appear in logs or non-secret columns.

For email: `webhook_url_*` is nullable; address lives in
`config_json` (with caller-supplied verified SES identity).

`enabled` lets the orchestrator soft-disable a misbehaving channel
without a row delete — the consumer's circuit breaker triggers on
delivery failures and flips this; an OrgAdmin re-enables once the
URL is corrected.

RLS-enforced.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, SMALLINT
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_channels",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.Text, nullable=False),  # slack | teams | email
        # KMS envelope columns — nullable so non-webhook channels (email)
        # can leave them empty. The repository enforces presence per channel.
        sa.Column("webhook_url_ciphertext", BYTEA),
        sa.Column("webhook_url_key_version", SMALLINT),
        sa.Column("webhook_url_iv", BYTEA),
        # Channel-specific public config: Slack `{channel_name}`, email
        # `{ses_identity, recipients}`, etc. Never secrets.
        sa.Column("config_json", JSONB),
        sa.Column(
            "enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "org_id", "channel", name="uq_notification_channels_org_channel"
        ),
    )
    op.execute("ALTER TABLE notification_channels ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notification_channels FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY org_isolation ON notification_channels
        USING (org_id = current_setting('app.current_org_id', true)::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.drop_table("notification_channels")

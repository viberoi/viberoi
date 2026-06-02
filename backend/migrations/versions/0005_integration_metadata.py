"""integration_oauth_tokens metadata columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-03

Adds the post-OAuth metadata that the Integration service captures
once a connection completes:

  - discovery_metadata JSONB — per-provider discovery data (Jira cloud_id +
    sprint_field_id, Linear organization_id + team ids, GitHub permissions +
    repository_selection). One JSONB column instead of per-provider columns
    keeps the schema generic; the orchestrator unpacks the dict.
  - webhook_registration_status TEXT — pending | ok | failed.
  - last_sync_at TIMESTAMPTZ — set by the backfill consumer after each
    successful sync (powers the "stale integration" indicator in the UI).
  - webhook_ids JSONB — list of provider-side webhook IDs we created so
    `disconnect` knows what to delete.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "integration_oauth_tokens",
        sa.Column("discovery_metadata", JSONB),
    )
    op.add_column(
        "integration_oauth_tokens",
        sa.Column("webhook_registration_status", sa.Text),
    )
    op.add_column(
        "integration_oauth_tokens",
        sa.Column("last_sync_at", sa.TIMESTAMP(timezone=True)),
    )
    op.add_column(
        "integration_oauth_tokens",
        sa.Column("webhook_ids", JSONB),
    )


def downgrade() -> None:
    op.drop_column("integration_oauth_tokens", "webhook_ids")
    op.drop_column("integration_oauth_tokens", "last_sync_at")
    op.drop_column("integration_oauth_tokens", "webhook_registration_status")
    op.drop_column("integration_oauth_tokens", "discovery_metadata")

"""tickets, sprints, integration_oauth_tokens

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-02

Slice 4 schema additions:
  - sprints (populated by Integration service from Jira / Linear / GH milestones)
  - tickets (populated by Integration service; powers attribution Signals 2/3/4)
  - integration_oauth_tokens (KMS-encrypted access/refresh tokens and the
    per-org webhook signing secret used by the webhook Lambda)

All tables RLS-enforced with FORCE + the standard org_isolation policy.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, NUMERIC
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY org_isolation ON {table}
        USING (org_id = current_setting('app.current_org_id', true)::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
        """
    )


def upgrade() -> None:
    # ── sprints ────────────────────────────────────────────────────────────
    op.create_table(
        "sprints",
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
        sa.Column("system", sa.Text, nullable=False),  # jira | linear | github_milestone
        sa.Column("external_id", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("state", sa.Text, nullable=False, server_default="future"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("board_id", sa.Text),
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
            "org_id",
            "system",
            "external_id",
            name="uq_sprints_org_system_external",
        ),
    )
    op.create_index("ix_sprints_org_state", "sprints", ["org_id", "state"])
    _enable_rls("sprints")

    # ── tickets ────────────────────────────────────────────────────────────
    op.create_table(
        "tickets",
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
        sa.Column("system", sa.Text, nullable=False),
        sa.Column("external_id", sa.Text, nullable=False),  # e.g. "JIRA-142"
        sa.Column("title", sa.Text, nullable=False),  # titles OK per spec
        sa.Column("status", sa.Text, nullable=False),
        sa.Column(
            "assignee_developer_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("developers.id", ondelete="SET NULL"),
        ),
        sa.Column("epic_external_id", sa.Text),
        sa.Column(
            "sprint_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("sprints.id", ondelete="SET NULL"),
        ),
        sa.Column("story_points", NUMERIC(8, 2)),
        sa.Column("priority", sa.Text),
        sa.Column("created_at_external", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("closed_at_external", sa.TIMESTAMP(timezone=True)),
        # PR file paths from GitHub — powers attribution Signal 2 (file overlap).
        sa.Column(
            "pr_file_paths",
            ARRAY(sa.Text),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
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
            "org_id",
            "system",
            "external_id",
            name="uq_tickets_org_system_external",
        ),
    )
    op.create_index("ix_tickets_org_external", "tickets", ["org_id", "external_id"])
    op.create_index(
        "ix_tickets_org_sprint",
        "tickets",
        ["org_id", "sprint_id"],
        postgresql_where=sa.text("sprint_id IS NOT NULL"),
    )
    op.create_index("ix_tickets_org_status", "tickets", ["org_id", "status"])
    op.create_index(
        "ix_tickets_org_assignee",
        "tickets",
        ["org_id", "assignee_developer_id"],
        postgresql_where=sa.text("assignee_developer_id IS NOT NULL"),
    )
    op.create_index(
        "ix_tickets_org_epic",
        "tickets",
        ["org_id", "epic_external_id"],
        postgresql_where=sa.text("epic_external_id IS NOT NULL"),
    )
    _enable_rls("tickets")

    # ── integration_oauth_tokens ──────────────────────────────────────────
    op.create_table(
        "integration_oauth_tokens",
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
        sa.Column("provider", sa.Text, nullable=False),
        # KMS-encrypted access token
        sa.Column("access_token_ciphertext", BYTEA, nullable=False),
        sa.Column("access_token_key_version", sa.SmallInteger, nullable=False),
        sa.Column("access_token_iv", BYTEA, nullable=False),
        # KMS-encrypted refresh token (some OAuth flows don't issue one)
        sa.Column("refresh_token_ciphertext", BYTEA),
        sa.Column("refresh_token_key_version", sa.SmallInteger),
        sa.Column("refresh_token_iv", BYTEA),
        # KMS-encrypted webhook signing secret — looked up by the webhook
        # Lambda per request and passed to viberoi_shared.webhooks.verify().
        sa.Column("webhook_secret_ciphertext", BYTEA),
        sa.Column("webhook_secret_key_version", sa.SmallInteger),
        sa.Column("webhook_secret_iv", BYTEA),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("scope", sa.Text),
        sa.Column("installation_id", sa.Text),  # GitHub App installations
        sa.Column(
            "installed_by_developer_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("developers.id", ondelete="SET NULL"),
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
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True)),
        # V1: one active token per (org, provider). Multi-installation per
        # org (e.g. GitHub App across multiple sub-orgs) is V2.
        sa.UniqueConstraint("org_id", "provider", name="uq_oauth_org_provider"),
    )
    op.create_index(
        "ix_oauth_org_provider", "integration_oauth_tokens", ["org_id", "provider"]
    )
    _enable_rls("integration_oauth_tokens")


def downgrade() -> None:
    op.drop_table("integration_oauth_tokens")
    op.drop_table("tickets")
    op.drop_table("sprints")

"""initial schema: orgs, teams, developers, org_tokens, sessions, RLS

Revision ID: 0001
Revises:
Create Date: 2026-06-02

The first migration. Establishes the core tenant model:
  - orgs (the tenant boundary)
  - teams (within an org)
  - developers (Cognito sub + encrypted PII)
  - org_tokens (Argon2id-hashed agent tokens)
  - sessions (the locked v1.0 schema as DB rows)

Every org-scoped table has RLS enabled and an `org_isolation` policy that
matches `org_id = current_setting('app.current_org_id', true)::uuid`.
The regular `viberoi` user respects RLS; the `viberoi_admin` (BYPASSRLS)
role used by this migration is the only escape hatch.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, NUMERIC, UUID

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enable_rls(table: str) -> None:
    """Turn on RLS and add the standard org_isolation policy."""
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY org_isolation ON {table}
        USING (org_id = current_setting('app.current_org_id', true)::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
        """
    )


def upgrade() -> None:
    # ── orgs ────────────────────────────────────────────────────────────────
    op.create_table(
        "orgs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("domain", sa.Text, nullable=False, unique=True),
        sa.Column("name_ciphertext", BYTEA, nullable=False),
        sa.Column("name_key_version", sa.SmallInteger, nullable=False),
        sa.Column("name_iv", BYTEA, nullable=False),
        sa.Column("plan", sa.Text, nullable=False, server_default="trial"),
        sa.Column("trial_ends_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("billing_email_ciphertext", BYTEA),
        sa.Column("billing_email_key_version", sa.SmallInteger),
        sa.Column("billing_email_iv", BYTEA),
        sa.Column("billing_email_hash", BYTEA),
        sa.Column("settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
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
    )
    op.create_index("ix_orgs_domain", "orgs", ["domain"])

    # RLS on orgs: a request scoped to an org can only see its own row.
    op.execute("ALTER TABLE orgs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY org_isolation ON orgs
        USING (id = current_setting('app.current_org_id', true)::uuid)
        WITH CHECK (id = current_setting('app.current_org_id', true)::uuid)
        """
    )

    # ── teams ───────────────────────────────────────────────────────────────
    op.create_table(
        "teams",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
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
        sa.UniqueConstraint("org_id", "name", name="uq_teams_org_name"),
    )
    op.create_index("ix_teams_org", "teams", ["org_id"])
    _enable_rls("teams")

    # ── developers ──────────────────────────────────────────────────────────
    op.create_table(
        "developers",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cognito_sub", sa.Text, nullable=False, unique=True),
        sa.Column(
            "team_id",
            UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
        ),
        sa.Column("role", sa.Text, nullable=False, server_default="Developer"),
        # Encrypted PII — see .claude/rules/security.md
        sa.Column("email_ciphertext", BYTEA, nullable=False),
        sa.Column("email_key_version", sa.SmallInteger, nullable=False),
        sa.Column("email_iv", BYTEA, nullable=False),
        sa.Column("email_hash", BYTEA, nullable=False),  # HMAC for lookup
        sa.Column("full_name_ciphertext", BYTEA),
        sa.Column("full_name_key_version", sa.SmallInteger),
        sa.Column("full_name_iv", BYTEA),
        sa.Column("github_username_ciphertext", BYTEA),
        sa.Column("github_username_key_version", sa.SmallInteger),
        sa.Column("github_username_iv", BYTEA),
        sa.Column("github_username_hash", BYTEA),  # HMAC for invitation lookup
        # Non-PII
        sa.Column("hourly_rate_usd", NUMERIC(10, 2)),
        sa.Column("machine_id_hash", BYTEA),  # HMAC; cross-org fingerprint
        sa.Column("agent_status", sa.Text, nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_active_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("org_id", "email_hash", name="uq_developers_org_email"),
    )
    op.create_index("ix_developers_org", "developers", ["org_id"])
    op.create_index("ix_developers_email_hash", "developers", ["email_hash"])
    op.create_index(
        "ix_developers_github_hash",
        "developers",
        ["github_username_hash"],
        postgresql_where=sa.text("github_username_hash IS NOT NULL"),
    )
    op.create_index(
        "ix_developers_machine_id",
        "developers",
        ["machine_id_hash"],
        postgresql_where=sa.text("machine_id_hash IS NOT NULL"),
    )
    _enable_rls("developers")

    # ── org_tokens ──────────────────────────────────────────────────────────
    op.create_table(
        "org_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "developer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("developers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hashed", sa.Text, nullable=False),  # Argon2id self-describing
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index("ix_org_tokens_org_dev", "org_tokens", ["org_id", "developer_id"])
    _enable_rls("org_tokens")

    # ── sessions (the locked v1.0 schema, flattened to columns) ─────────────
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", sa.Text, nullable=False),  # external tool's session ID
        sa.Column(
            "developer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("developers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Tool
        sa.Column("tool_name", sa.Text, nullable=False),
        sa.Column("tool_surface", sa.Text, nullable=False),
        sa.Column("tool_version", sa.Text, nullable=False),
        sa.Column("tool_model", sa.Text, nullable=False),
        sa.Column("tool_capture_mode", sa.Text, nullable=False),
        sa.Column("tool_pricing_type", sa.Text, nullable=False),
        sa.Column("tool_pricing_unit", sa.Text, nullable=False),
        sa.Column("tool_pricing_rate_usd", NUMERIC(20, 12), nullable=False),
        # Timing
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("active_duration_min", sa.Integer, nullable=False),
        sa.Column("first_commit_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("time_to_first_commit_min", sa.Integer),
        # Tokens
        sa.Column("tokens_input", sa.BigInteger, nullable=False),
        sa.Column("tokens_output", sa.BigInteger, nullable=False),
        sa.Column("tokens_cache_read", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("tokens_cache_write", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", NUMERIC(20, 8), nullable=False),
        sa.Column("is_estimated", sa.Boolean, nullable=False),
        sa.Column("reconciled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("reconciled_at", sa.TIMESTAMP(timezone=True)),
        # Activity
        sa.Column("turn_count", sa.Integer, nullable=False),
        sa.Column("mode", sa.Text, nullable=False),
        sa.Column("is_agentic", sa.Boolean, nullable=False),
        sa.Column("subagent_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "files_touched",
            ARRAY(sa.Text),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("files_touched_count", sa.Integer, nullable=False, server_default="0"),
        # Code output
        sa.Column("lines_added", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lines_deleted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lines_accepted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lines_reverted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_committed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "commit_hashes",
            ARRAY(sa.Text),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "uncommitted_at_end", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        # Repository
        sa.Column("repo_name", sa.Text, nullable=False),
        sa.Column("repo_origin_cwd", sa.Text, nullable=False),
        sa.Column("repo_branch", sa.Text, nullable=False),
        sa.Column("repo_raw_branch", sa.Text),
        sa.Column(
            "repo_is_worktree", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        # Attribution
        sa.Column("attr_ticket_id", sa.Text),
        sa.Column("attr_epic_id", sa.Text),
        sa.Column("attr_sprint_id", sa.Text),
        sa.Column("attr_confidence", NUMERIC(4, 3), nullable=False, server_default="0"),
        sa.Column(
            "attr_signals",
            ARRAY(sa.Text),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("attr_method", sa.Text, nullable=False, server_default="branch_parse"),
        # Quality
        sa.Column("quality_session_restarts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quality_file_oscillations", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "quality_token_spike_detected",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "quality_no_commit_duration_min", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "quality_is_refunded", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "quality_hallucination_risk", sa.Text, nullable=False, server_default="none"
        ),
        # Meta
        sa.Column("captured_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("agent_version", sa.Text, nullable=False),
        sa.Column(
            "data_sources",
            ARRAY(sa.Text),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("schema_version", sa.Text, nullable=False),
        # Bookkeeping
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
        sa.UniqueConstraint("org_id", "session_id", name="uq_sessions_org_session"),
    )

    # Indexes — sized for the KPI queries listed in
    # `frontend/VibeROI-DataSource-Master-final.md` § Q15.
    op.create_index("ix_sessions_org_started", "sessions", ["org_id", "started_at"])
    op.create_index(
        "ix_sessions_org_ticket",
        "sessions",
        ["org_id", "attr_ticket_id"],
        postgresql_where=sa.text("attr_ticket_id IS NOT NULL"),
    )
    op.create_index(
        "ix_sessions_org_sprint",
        "sessions",
        ["org_id", "attr_sprint_id"],
        postgresql_where=sa.text("attr_sprint_id IS NOT NULL"),
    )
    op.create_index(
        "ix_sessions_org_developer",
        "sessions",
        ["org_id", "developer_id", "started_at"],
    )
    op.create_index(
        "ix_sessions_unknown_queue",
        "sessions",
        ["org_id", "attr_confidence"],
        postgresql_where=sa.text("attr_confidence < 0.5"),
    )
    op.create_index(
        "ix_sessions_reconciled",
        "sessions",
        ["reconciled", "captured_at"],
        postgresql_where=sa.text("reconciled = false"),
    )

    _enable_rls("sessions")


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("org_tokens")
    op.drop_table("developers")
    op.drop_table("teams")
    op.drop_table("orgs")

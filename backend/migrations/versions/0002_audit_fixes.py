"""schema audit fixes from slice 1 review

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-02

Adds three small refinements identified in the Slice 1 review:

  - teams.lead_developer_id (FK developers) — admins assign a Team Lead per
    FSD §S-09 Manage Team; nullable until set.
  - developers UNIQUE(org_id, machine_id_hash) — same machine should not
    double-register in one org (cross-org fingerprint still works without
    this constraint).
  - org_tokens.device_label — human-readable label like "Adnan's MacBook"
    for the "X of 5 devices installed" UI per Q10/onboarding Step 5.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── teams.lead_developer_id ────────────────────────────────────────
    op.add_column(
        "teams",
        sa.Column(
            "lead_developer_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey(
                "developers.id",
                ondelete="SET NULL",
                name="fk_teams_lead_developer",
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_teams_lead_developer",
        "teams",
        ["lead_developer_id"],
        postgresql_where=sa.text("lead_developer_id IS NOT NULL"),
    )

    # ── developers UNIQUE(org_id, machine_id_hash) ─────────────────────
    # Allows nulls — only enforced when machine_id_hash is set.
    op.create_unique_constraint(
        "uq_developers_org_machine",
        "developers",
        ["org_id", "machine_id_hash"],
    )

    # ── org_tokens.device_label ────────────────────────────────────────
    op.add_column(
        "org_tokens",
        sa.Column("device_label", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("org_tokens", "device_label")
    op.drop_constraint(
        "uq_developers_org_machine", "developers", type_="unique"
    )
    op.drop_index("ix_teams_lead_developer", table_name="teams")
    op.drop_constraint("fk_teams_lead_developer", "teams", type_="foreignkey")
    op.drop_column("teams", "lead_developer_id")

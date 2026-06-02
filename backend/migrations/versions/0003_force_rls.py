"""apply FORCE ROW LEVEL SECURITY on existing tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-02

Slice-3 hardening: without `FORCE ROW LEVEL SECURITY`, Postgres lets
the table OWNER bypass RLS — and the owner here is viberoi_admin (the
role Alembic runs as). FORCE means even the owner is subject to policy.

Migration 0001 was updated to apply FORCE on fresh installs; this
migration brings already-deployed databases up to that state. Idempotent —
re-running on a table that's already FORCE is a no-op.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ["orgs", "teams", "developers", "org_tokens", "sessions"]


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")

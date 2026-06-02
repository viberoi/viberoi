"""Declarative base for all SQLAlchemy ORM models.

Every model that holds org-scoped data must:
  1. Inherit from `Base`.
  2. Declare `org_id: Mapped[UUID]` with a foreign key to `orgs.id`.
  3. Have a matching RLS policy in the Alembic migration:
       CREATE POLICY org_isolation ON <table>
         USING (org_id = current_setting('app.current_org_id')::uuid);

PII columns follow the encryption pattern documented in
`.claude/rules/security.md`:
  <field>_ciphertext BYTEA NOT NULL
  <field>_key_version SMALLINT NOT NULL
  <field>_iv BYTEA NOT NULL
  <field>_hash BYTEA          -- optional, for searchable lookup
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all viberoi ORM models."""

# Migrations

Alembic-managed schema for VibeROI. Single source of truth for tables, indexes, and **RLS policies**.

## Conventions

- One migration per logical change. Don't bundle unrelated tables in one revision.
- Sequential numeric revision IDs (`0001`, `0002`, ...) — easier to read than UUIDs.
- Every table holding org-scoped data MUST have an RLS policy in the same migration that creates it.
- PII columns use the `(<field>_ciphertext BYTEA, <field>_key_version SMALLINT, <field>_iv BYTEA)` shape. Add `<field>_hash BYTEA` when the column needs lookup (HMAC).
- Use `op.execute()` for RLS, custom indexes, and anything Alembic autogenerate can't express.
- Always implement `downgrade()` — even just `op.drop_table()`.

## Commands

All run from the repo root (root `pyproject.toml` is the workspace owner):

```powershell
# Apply all pending migrations
uv run alembic -c backend/migrations/alembic.ini upgrade head

# Create a new revision (autogenerate from ORM model diffs)
uv run alembic -c backend/migrations/alembic.ini revision --autogenerate -m "add foo table"

# Create an empty revision (when autogenerate can't see the change, e.g. RLS-only)
uv run alembic -c backend/migrations/alembic.ini revision -m "add rls policy on x"

# Show current revision
uv run alembic -c backend/migrations/alembic.ini current

# Roll back one revision
uv run alembic -c backend/migrations/alembic.ini downgrade -1
```

A shorter alias lives in the root `pyproject.toml` once we wire it; for now the `-c` flag is explicit.

## Who connects

Alembic uses `viberoi_shared.config.SharedSettings.database_admin_url` — the **BYPASSRLS** role (`viberoi_admin`). This is the same role used by `viberoi_shared.db.superuser_session()` for cross-org admin tasks.

**Services and request handlers never use this URL.** They use `database_url` (regular `viberoi` user) via `org_scoped_session(org_id)`, which sets `app.current_org_id` so RLS enforces tenant isolation.

## Reviewing a migration

Before merging:

1. Read the SQL: `alembic upgrade head --sql` (emits without applying).
2. Confirm RLS is enabled on every new org-scoped table.
3. Confirm PII columns follow the encrypted-shape convention.
4. Confirm indexes exist for foreseeable KPI queries (`(org_id, <time field>)`, etc.).
5. Confirm `downgrade()` actually reverses the change.

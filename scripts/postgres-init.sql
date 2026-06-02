-- VibeROI local Postgres setup.
-- Runs once on first container start (via /docker-entrypoint-initdb.d/),
-- executed as the bootstrap superuser `postgres`. This file is the ONLY
-- place where the two app roles are created — never use the `postgres`
-- superuser from app code.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── viberoi — regular role used at runtime (RLS-respecting) ────────────────
-- Request handlers connect as this role via `org_scoped_session(org_id)`.
-- NOT a superuser, does NOT bypass RLS — RLS is the safety net we want.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'viberoi') THEN
        CREATE ROLE viberoi WITH LOGIN PASSWORD 'viberoi' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE viberoi TO viberoi;
GRANT USAGE ON SCHEMA public TO viberoi;

-- ── viberoi_admin — admin role used by Alembic + cross-org admin tasks ───
-- BYPASSRLS so migrations can manage policies + the superuser_session()
-- helper can do cross-tenant bookkeeping (KPI snapshot cron, cleanups).
-- NOT a Postgres SUPERUSER — BYPASSRLS is the only special privilege.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'viberoi_admin') THEN
        CREATE ROLE viberoi_admin WITH LOGIN PASSWORD 'viberoi_admin'
            NOSUPERUSER BYPASSRLS;
    END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE viberoi TO viberoi_admin;
GRANT ALL ON SCHEMA public TO viberoi_admin;

-- Default privileges: tables/sequences CREATED BY viberoi_admin (Alembic)
-- automatically grant CRUD + sequence usage to viberoi at create time.
-- Without `FOR ROLE viberoi_admin`, the defaults would only apply to
-- objects created by `postgres` — and our tables aren't.
ALTER DEFAULT PRIVILEGES FOR ROLE viberoi_admin IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO viberoi;
ALTER DEFAULT PRIVILEGES FOR ROLE viberoi_admin IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO viberoi;

-- Note: `app.current_org_id` is a session-local GUC set via
-- `set_config('app.current_org_id', '<uuid>', true)` inside a transaction
-- (see `viberoi_shared.db.session.org_scoped_session`). No ALTER SYSTEM
-- needed — Postgres accepts arbitrary custom GUCs when set with is_local=true.

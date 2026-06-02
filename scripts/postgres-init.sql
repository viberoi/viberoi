-- VibeROI local Postgres setup.
-- Runs once on first container start (via /docker-entrypoint-initdb.d/).
-- The main DB and `viberoi` user are created by POSTGRES_USER / POSTGRES_DB env vars
-- in docker-compose.yml. This script adds: extensions and the admin role.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- BYPASSRLS role — used ONLY by `viberoi_shared.db.superuser_session()` and
-- by Alembic migrations. The regular `viberoi` user RESPECTS RLS, so request
-- handlers go through the regular user via `org_scoped_session(org_id)`.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'viberoi_admin') THEN
        CREATE ROLE viberoi_admin WITH LOGIN PASSWORD 'viberoi_admin' BYPASSRLS;
    END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE viberoi TO viberoi_admin;
GRANT ALL ON SCHEMA public TO viberoi_admin;

-- Note: `app.current_org_id` is a session-local GUC set via
-- `set_config('app.current_org_id', '<uuid>', true)` inside a transaction
-- (see `viberoi_shared.db.session.org_scoped_session`). No ALTER SYSTEM
-- needed — Postgres accepts arbitrary custom GUCs when set with is_local=true.

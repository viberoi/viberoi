"""Async SQLAlchemy engines + session factories.

Two engines per process:
  - Regular engine — connects as the RLS-respecting `viberoi` role.
    Used by `org_scoped_session(org_id)` (the only path for request handlers).
  - Admin engine — connects as the BYPASSRLS `viberoi_admin` role.
    Used only by `superuser_session()` for cross-org admin tasks.

Both lazily initialized on first call.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from viberoi_shared.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_admin_engine: AsyncEngine | None = None
_admin_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the regular (RLS-respecting) AsyncEngine. Idempotent."""
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_async_engine(
            s.database_url,
            pool_size=s.database_pool_size,
            max_overflow=s.database_max_overflow,
            pool_timeout=s.database_pool_timeout_s,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the regular session factory. Idempotent."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


def get_admin_engine() -> AsyncEngine:
    """Return the admin (BYPASSRLS) AsyncEngine. Idempotent.

    The admin URL stored in settings uses the sync `+psycopg` driver
    (for Alembic). We swap to `+asyncpg` here for async use. Small pool —
    admin sessions are infrequent (cron jobs, cross-org admin tasks).
    """
    global _admin_engine
    if _admin_engine is None:
        s = get_settings()
        async_admin_url = s.database_admin_url.replace("+psycopg", "+asyncpg")
        _admin_engine = create_async_engine(
            async_admin_url,
            pool_size=2,
            max_overflow=3,
            pool_timeout=s.database_pool_timeout_s,
            pool_pre_ping=True,
            echo=False,
        )
    return _admin_engine


def get_admin_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the admin session factory. Idempotent."""
    global _admin_session_factory
    if _admin_session_factory is None:
        _admin_session_factory = async_sessionmaker(
            bind=get_admin_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _admin_session_factory


async def dispose_engine() -> None:
    """Close all engines (call on shutdown)."""
    global _engine, _session_factory, _admin_engine, _admin_session_factory
    if _engine is not None:
        await _engine.dispose()
    if _admin_engine is not None:
        await _admin_engine.dispose()
    _engine = None
    _session_factory = None
    _admin_engine = None
    _admin_session_factory = None

"""Async SQLAlchemy engine + session factory.

One engine per process; initialized lazily on first call.
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


def get_engine() -> AsyncEngine:
    """Return the process-wide AsyncEngine. Idempotent."""
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
    """Return the process-wide session factory. Idempotent."""
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


async def dispose_engine() -> None:
    """Close the engine (call on shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None

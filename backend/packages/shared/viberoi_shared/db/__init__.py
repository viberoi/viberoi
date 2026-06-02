"""Async SQLAlchemy engine, org-scoped session factory, RLS context.

Services obtain a DB session exclusively via `org_scoped_session(org_id)`.
The helper sets `app.current_org_id` GUC so Postgres RLS enforces
tenant isolation even if app code forgets to filter.
"""

from viberoi_shared.db.base import Base
from viberoi_shared.db.engine import dispose_engine, get_engine, get_session_factory
from viberoi_shared.db.session import OrgContextError, org_scoped_session, superuser_session

__all__ = [
    "Base",
    "OrgContextError",
    "dispose_engine",
    "get_engine",
    "get_session_factory",
    "org_scoped_session",
    "superuser_session",
]

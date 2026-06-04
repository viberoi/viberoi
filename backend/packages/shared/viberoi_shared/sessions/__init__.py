"""CRUD + ORM for the locked session schema (v1.0).

Services pass `viberoi_shared.types.session.Session` (Pydantic) objects;
the repository handles the flatten/inflate to `SessionRow` (ORM).
Services never touch `SessionRow` or write SQL inline.
"""

from viberoi_shared.sessions.models import SessionRow
from viberoi_shared.sessions.repository import (
    SESSION_LIST_DEFAULT,
    SESSION_LIST_HARD_CAP,
    get_by_external_id,
    get_by_id,
    list_sessions,
    list_sessions_for_ticket,
    upsert,
)

__all__ = [
    "SESSION_LIST_DEFAULT",
    "SESSION_LIST_HARD_CAP",
    "SessionRow",
    "get_by_external_id",
    "get_by_id",
    "list_sessions",
    "list_sessions_for_ticket",
    "upsert",
]

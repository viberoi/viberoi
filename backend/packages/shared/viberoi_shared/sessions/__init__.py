"""CRUD + ORM for the locked session schema (v1.0).

Services pass `viberoi_shared.types.session.Session` (Pydantic) objects;
the repository handles the flatten/inflate to `SessionRow` (ORM).
Services never touch `SessionRow` or write SQL inline.
"""

from viberoi_shared.sessions.models import SessionRow
from viberoi_shared.sessions.repository import get_by_external_id, get_by_id, upsert

__all__ = [
    "SessionRow",
    "get_by_external_id",
    "get_by_id",
    "upsert",
]

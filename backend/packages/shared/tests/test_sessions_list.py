"""Tests for `list_sessions` — pagination + role-based filtering.

Unit-level tests for the cursor encode/decode round-trip + the
ValidationFailed path on a malformed cursor. The full integration test
(against real Postgres) is implicit through other integration runs in
later batches.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from viberoi_shared.errors import ValidationFailed
from viberoi_shared.sessions.repository import _decode_cursor, _encode_cursor


def test_cursor_round_trip() -> None:
    ts = datetime(2026, 6, 3, 12, 34, 56, tzinfo=UTC)
    uid = uuid4()
    cursor = _encode_cursor(ts, uid)
    out_ts, out_uid = _decode_cursor(cursor)
    assert out_ts == ts
    assert out_uid == uid


def test_cursor_is_url_safe() -> None:
    """No `+` or `/` in the cursor — URL-safe base64."""
    ts = datetime.now(tz=UTC)
    cursor = _encode_cursor(ts, uuid4())
    assert "+" not in cursor
    assert "/" not in cursor
    # No padding = either — we strip it on encode and restore on decode.
    assert "=" not in cursor


def test_decode_rejects_garbage() -> None:
    with pytest.raises(ValidationFailed):
        _decode_cursor("not-a-cursor!!!")


def test_decode_rejects_truncated() -> None:
    ts = datetime.now(tz=UTC)
    cursor = _encode_cursor(ts, uuid4())
    # Lop off most of the string — base64 decode succeeds but split fails.
    with pytest.raises(ValidationFailed):
        _decode_cursor(cursor[:4])


def test_decode_rejects_missing_separator() -> None:
    import base64

    raw = "no-separator-here"
    cursor = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    with pytest.raises(ValidationFailed):
        _decode_cursor(cursor)

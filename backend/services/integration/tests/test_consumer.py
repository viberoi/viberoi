"""Unit tests for `integration.app.consumer._handle_message`.

Mocks SQS + `run_sync`; we just want to verify ack/no-ack semantics +
envelope parsing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import orjson
import pytest
from integration.app import consumer

from viberoi_shared.errors import NotFound


@pytest.fixture
def patch_io(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(consumer, "delete", AsyncMock())
    monkeypatch.setattr(consumer, "run_sync", AsyncMock())
    return consumer


def _msg(body: dict | str) -> dict:
    if isinstance(body, dict):
        body = orjson.dumps(body).decode()
    return {"MessageId": "m1", "ReceiptHandle": "rh1", "Body": body}


async def test_handle_message_happy_path_acks(patch_io) -> None:
    body = {
        "org_id": str(uuid4()),
        "provider": "github",
        "sync_type": "manual",
        "trace_id": str(uuid4()),
    }
    await patch_io._handle_message(_msg(body))
    patch_io.run_sync.assert_awaited_once()
    patch_io.delete.assert_awaited_once()


async def test_handle_message_bad_json_acks(patch_io) -> None:
    """Unrecoverable parse error → ack so it doesn't loop forever."""
    await patch_io._handle_message(_msg("not-json{"))
    patch_io.run_sync.assert_not_awaited()
    patch_io.delete.assert_awaited_once()


async def test_handle_message_invalid_sync_type_acks(patch_io) -> None:
    body = {
        "org_id": str(uuid4()),
        "provider": "github",
        "sync_type": "weekly",  # not in VALID_SYNC_TYPES
    }
    await patch_io._handle_message(_msg(body))
    patch_io.run_sync.assert_not_awaited()
    patch_io.delete.assert_awaited_once()


async def test_handle_message_notfound_acks(patch_io) -> None:
    """Integration was revoked between enqueue and process → ack, don't retry."""
    patch_io.run_sync.side_effect = NotFound("revoked")
    body = {
        "org_id": str(uuid4()),
        "provider": "jira",
        "sync_type": "delta",
    }
    await patch_io._handle_message(_msg(body))
    patch_io.delete.assert_awaited_once()


async def test_handle_message_processing_error_does_not_ack(patch_io) -> None:
    """Transient failure → DON'T ack so SQS redelivers."""
    patch_io.run_sync.side_effect = RuntimeError("boom")
    body = {
        "org_id": str(uuid4()),
        "provider": "linear",
        "sync_type": "delta",
    }
    await patch_io._handle_message(_msg(body))
    patch_io.delete.assert_not_awaited()

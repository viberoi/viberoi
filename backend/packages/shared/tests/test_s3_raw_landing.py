"""S3 raw-landing helpers — integration tests (requires LocalStack)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from viberoi_shared.s3 import (
    RAW_BUCKET,
    S3Error,
    get_raw_session,
    head_raw_session,
    put_raw_session,
    raw_landing_key,
)

pytestmark = pytest.mark.integration


def test_raw_landing_key_shape() -> None:
    ts = datetime(2026, 5, 6, 10, 42, 55, tzinfo=UTC)
    key = raw_landing_key("org-123", "session-abc", ts)
    assert key == "orgs/org-123/sessions/2026-05-06/session-abc.json.gz"


async def test_put_get_round_trip() -> None:
    org_id = uuid4()
    session_id = f"test-{uuid4()}"
    body = b'{"hello":"world"}'  # would normally be gzipped JSON
    ts = datetime.now(tz=UTC)

    key = await put_raw_session(
        org_id=org_id, session_id=session_id, captured_at=ts, body=body
    )
    assert key.startswith(f"orgs/{org_id}/sessions/")
    assert key.endswith(f"{session_id}.json.gz")

    assert await head_raw_session(key)
    got = await get_raw_session(key)
    assert got == body


async def test_get_missing_key_raises() -> None:
    with pytest.raises(S3Error):
        await get_raw_session(f"orgs/missing/{uuid4()}.json.gz")


async def test_head_missing_key_returns_false() -> None:
    assert not await head_raw_session(f"orgs/missing/{uuid4()}.json.gz")


async def test_raw_bucket_constant() -> None:
    assert RAW_BUCKET == "viberoi-org-data"

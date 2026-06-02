"""Auth header parsing — unit tests for `_parse_auth_headers`."""

from uuid import UUID, uuid4

import pytest
from starlette.requests import Request

from ingest.app.auth import _parse_auth_headers
from viberoi_shared.errors import Unauthorized


def _make_request(headers: dict[str, str]) -> Request:
    """Build a minimal Starlette Request with the given headers."""
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {"type": "http", "headers": raw_headers}
    return Request(scope)  # type: ignore[arg-type]


def test_parse_valid_headers() -> None:
    org_id = uuid4()
    dev_id = uuid4()
    request = _make_request(
        {
            "Authorization": "Bearer my-secret-token",
            "X-VibeROI-Org-Id": str(org_id),
            "X-VibeROI-Developer-Id": str(dev_id),
        }
    )
    parsed_org, parsed_dev, token = _parse_auth_headers(request)
    assert parsed_org == org_id
    assert parsed_dev == dev_id
    assert token == "my-secret-token"


def test_parse_rejects_missing_authorization() -> None:
    request = _make_request(
        {
            "X-VibeROI-Org-Id": str(uuid4()),
            "X-VibeROI-Developer-Id": str(uuid4()),
        }
    )
    with pytest.raises(Unauthorized):
        _parse_auth_headers(request)


def test_parse_rejects_non_bearer_scheme() -> None:
    request = _make_request(
        {
            "Authorization": "Basic somebase64",
            "X-VibeROI-Org-Id": str(uuid4()),
            "X-VibeROI-Developer-Id": str(uuid4()),
        }
    )
    with pytest.raises(Unauthorized):
        _parse_auth_headers(request)


def test_parse_rejects_empty_bearer_token() -> None:
    request = _make_request(
        {
            "Authorization": "Bearer   ",
            "X-VibeROI-Org-Id": str(uuid4()),
            "X-VibeROI-Developer-Id": str(uuid4()),
        }
    )
    with pytest.raises(Unauthorized):
        _parse_auth_headers(request)


def test_parse_rejects_invalid_org_uuid() -> None:
    request = _make_request(
        {
            "Authorization": "Bearer t",
            "X-VibeROI-Org-Id": "not-a-uuid",
            "X-VibeROI-Developer-Id": str(uuid4()),
        }
    )
    with pytest.raises(Unauthorized):
        _parse_auth_headers(request)


def test_parse_rejects_invalid_developer_uuid() -> None:
    request = _make_request(
        {
            "Authorization": "Bearer t",
            "X-VibeROI-Org-Id": str(uuid4()),
            "X-VibeROI-Developer-Id": "also-not-a-uuid",
        }
    )
    with pytest.raises(Unauthorized):
        _parse_auth_headers(request)


def test_parse_is_case_insensitive_for_bearer_scheme() -> None:
    request = _make_request(
        {
            "Authorization": "bearer my-token",
            "X-VibeROI-Org-Id": str(uuid4()),
            "X-VibeROI-Developer-Id": str(uuid4()),
        }
    )
    _, _, token = _parse_auth_headers(request)
    assert token == "my-token"

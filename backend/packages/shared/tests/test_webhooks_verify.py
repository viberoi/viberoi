"""Webhook HMAC verifiers — unit tests.

Schemes verified against current vendor docs 2026-06-03 (see verify.py
docstring for citations).
"""

import base64
import hashlib
import hmac
import time

import pytest

from viberoi_shared.errors import Unauthorized
from viberoi_shared.webhooks import (
    GITLAB_TIMESTAMP_TOLERANCE_S,
    extract_delivery_id,
    verify,
    verify_github,
    verify_gitlab,
    verify_linear,
)

_SECRET = b"my-webhook-signing-secret"


# ── helpers ─────────────────────────────────────────────────────────────────


def _gh_sig(body: bytes, secret: bytes = _SECRET) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def _linear_sig(body: bytes, secret: bytes = _SECRET) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def _gitlab_swh_headers(
    body: bytes,
    *,
    secret: bytes = _SECRET,
    webhook_id: str = "msg_01HX",
    ts: int | None = None,
    sig_override: str | None = None,
) -> dict[str, str]:
    """Build a valid Standard-Webhooks header set for GitLab."""
    if ts is None:
        ts = int(time.time())
    signed = f"{webhook_id}.{ts}.".encode() + body
    sig_b64 = base64.b64encode(
        hmac.new(secret, signed, hashlib.sha256).digest()
    ).decode("ascii")
    return {
        "webhook-id": webhook_id,
        "webhook-timestamp": str(ts),
        "webhook-signature": sig_override or f"v1,{sig_b64}",
    }


# ── GitHub ──────────────────────────────────────────────────────────────────


def test_github_valid_signature() -> None:
    body = b'{"action":"opened"}'
    verify_github({"X-Hub-Signature-256": _gh_sig(body)}, body, _SECRET)


def test_github_case_insensitive_header() -> None:
    body = b'{"a":1}'
    verify_github({"x-hub-signature-256": _gh_sig(body)}, body, _SECRET)


def test_github_missing_header() -> None:
    with pytest.raises(Unauthorized):
        verify_github({}, b"body", _SECRET)


def test_github_wrong_secret() -> None:
    body = b'{"a":1}'
    bad = _gh_sig(body, b"wrong-secret")
    with pytest.raises(Unauthorized):
        verify_github({"X-Hub-Signature-256": bad}, body, _SECRET)


def test_github_tampered_body() -> None:
    body = b'{"a":1}'
    sig = _gh_sig(body)
    with pytest.raises(Unauthorized):
        verify_github({"X-Hub-Signature-256": sig}, b'{"a":2}', _SECRET)


def test_github_non_sha256_prefix() -> None:
    with pytest.raises(Unauthorized):
        verify_github({"X-Hub-Signature-256": "md5=somehash"}, b"body", _SECRET)


# ── GitLab — Standard Webhooks (new HMAC scheme) ────────────────────────────


def test_gitlab_swh_valid() -> None:
    body = b'{"object_kind":"push"}'
    verify_gitlab(_gitlab_swh_headers(body), body, _SECRET)


def test_gitlab_swh_tampered_body() -> None:
    body = b'{"a":1}'
    headers = _gitlab_swh_headers(body)
    with pytest.raises(Unauthorized):
        verify_gitlab(headers, b'{"a":2}', _SECRET)


def test_gitlab_swh_wrong_secret() -> None:
    body = b'{"a":1}'
    headers = _gitlab_swh_headers(body, secret=b"wrong-secret")
    with pytest.raises(Unauthorized):
        verify_gitlab(headers, body, _SECRET)


def test_gitlab_swh_rejects_old_timestamp() -> None:
    body = b'{"a":1}'
    old_ts = int(time.time()) - GITLAB_TIMESTAMP_TOLERANCE_S - 10
    headers = _gitlab_swh_headers(body, ts=old_ts)
    with pytest.raises(Unauthorized):
        verify_gitlab(headers, body, _SECRET)


def test_gitlab_swh_rejects_non_numeric_timestamp() -> None:
    body = b'{"a":1}'
    headers = _gitlab_swh_headers(body)
    headers["webhook-timestamp"] = "not-a-number"
    with pytest.raises(Unauthorized):
        verify_gitlab(headers, body, _SECRET)


def test_gitlab_swh_accepts_multiple_signatures_for_rotation() -> None:
    body = b'{"x":1}'
    headers = _gitlab_swh_headers(body)
    real_sig = headers["webhook-signature"]
    fake_sig = "v1,AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    # Space-separated tokens, real one second — should still pass
    headers["webhook-signature"] = f"{fake_sig} {real_sig}"
    verify_gitlab(headers, body, _SECRET)


def test_gitlab_swh_rejects_unknown_version_prefix() -> None:
    body = b'{"x":1}'
    headers = _gitlab_swh_headers(body)
    headers["webhook-signature"] = "v999,abc=="
    with pytest.raises(Unauthorized):
        verify_gitlab(headers, body, _SECRET)


# ── GitLab — legacy bearer (still supported during migration) ───────────────


def test_gitlab_legacy_matching_token() -> None:
    verify_gitlab({"X-Gitlab-Token": _SECRET.decode()}, b"any body", _SECRET)


def test_gitlab_legacy_wrong_token() -> None:
    with pytest.raises(Unauthorized):
        verify_gitlab({"X-Gitlab-Token": "wrong"}, b"body", _SECRET)


def test_gitlab_no_headers_at_all() -> None:
    with pytest.raises(Unauthorized):
        verify_gitlab({}, b"body", _SECRET)


# ── Linear ──────────────────────────────────────────────────────────────────


def test_linear_valid_signature() -> None:
    body = b'{"webhook":"linear"}'
    verify_linear({"Linear-Signature": _linear_sig(body)}, body, _SECRET)


def test_linear_missing_header() -> None:
    with pytest.raises(Unauthorized):
        verify_linear({}, b"body", _SECRET)


def test_linear_tampered_body() -> None:
    body = b'{"a":1}'
    sig = _linear_sig(body)
    with pytest.raises(Unauthorized):
        verify_linear({"Linear-Signature": sig}, b'{"a":2}', _SECRET)


# ── Dispatcher ──────────────────────────────────────────────────────────────


def test_dispatch_github() -> None:
    body = b'{"x":1}'
    verify("github", {"X-Hub-Signature-256": _gh_sig(body)}, body, _SECRET)


def test_dispatch_gitlab_swh() -> None:
    body = b'{"x":1}'
    verify("gitlab", _gitlab_swh_headers(body), body, _SECRET)


def test_dispatch_gitlab_legacy() -> None:
    verify("gitlab", {"X-Gitlab-Token": _SECRET.decode()}, b"body", _SECRET)


def test_dispatch_linear() -> None:
    body = b'{"x":1}'
    verify("linear", {"Linear-Signature": _linear_sig(body)}, body, _SECRET)


def test_dispatch_case_insensitive_provider() -> None:
    body = b"body"
    verify("GitHub", {"X-Hub-Signature-256": _gh_sig(body)}, body, _SECRET)


def test_dispatch_unknown_provider() -> None:
    with pytest.raises(Unauthorized):
        verify("bitbucket", {}, b"body", _SECRET)


# ── extract_delivery_id ─────────────────────────────────────────────────────


def test_extract_delivery_id_github() -> None:
    assert (
        extract_delivery_id(
            "github", {"X-GitHub-Delivery": "72d3162e-cc78-11e3-81ab-4c9367dc0958"}
        )
        == "72d3162e-cc78-11e3-81ab-4c9367dc0958"
    )


def test_extract_delivery_id_github_missing() -> None:
    assert extract_delivery_id("github", {}) is None


def test_extract_delivery_id_gitlab_standard_webhooks() -> None:
    assert (
        extract_delivery_id("gitlab", {"webhook-id": "msg_01HX9PVA"})
        == "msg_01HX9PVA"
    )


def test_extract_delivery_id_gitlab_legacy() -> None:
    assert extract_delivery_id("gitlab", {"X-Gitlab-Token": "secret"}) is None


def test_extract_delivery_id_linear() -> None:
    assert (
        extract_delivery_id(
            "linear", {"Linear-Delivery": "01HX9PVA-deliv-uuid"}
        )
        == "01HX9PVA-deliv-uuid"
    )


def test_extract_delivery_id_linear_missing() -> None:
    assert extract_delivery_id("linear", {"Linear-Signature": "abc"}) is None


def test_extract_delivery_id_unknown_provider_none() -> None:
    assert extract_delivery_id("bitbucket", {}) is None

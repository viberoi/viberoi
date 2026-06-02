"""Webhook HMAC verifiers — unit tests."""

import hashlib
import hmac

import pytest

from viberoi_shared.errors import Unauthorized
from viberoi_shared.webhooks import (
    verify,
    verify_github,
    verify_gitlab,
    verify_linear,
)

_SECRET = b"my-webhook-signing-secret"


def _gh_sig(body: bytes, secret: bytes = _SECRET) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def _linear_sig(body: bytes, secret: bytes = _SECRET) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


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
    tampered = b'{"a":2}'
    with pytest.raises(Unauthorized):
        verify_github({"X-Hub-Signature-256": sig}, tampered, _SECRET)


def test_github_non_sha256_prefix() -> None:
    body = b"body"
    with pytest.raises(Unauthorized):
        verify_github({"X-Hub-Signature-256": "md5=somehash"}, body, _SECRET)


# ── GitLab ──────────────────────────────────────────────────────────────────


def test_gitlab_matching_token() -> None:
    verify_gitlab({"X-Gitlab-Token": _SECRET.decode()}, b"any body", _SECRET)


def test_gitlab_wrong_token() -> None:
    with pytest.raises(Unauthorized):
        verify_gitlab({"X-Gitlab-Token": "wrong"}, b"body", _SECRET)


def test_gitlab_missing_token() -> None:
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


def test_dispatch_linear() -> None:
    body = b'{"x":1}'
    verify("linear", {"Linear-Signature": _linear_sig(body)}, body, _SECRET)


def test_dispatch_gitlab() -> None:
    verify("gitlab", {"X-Gitlab-Token": _SECRET.decode()}, b"body", _SECRET)


def test_dispatch_case_insensitive_provider() -> None:
    body = b"body"
    verify("GitHub", {"X-Hub-Signature-256": _gh_sig(body)}, body, _SECRET)


def test_dispatch_unknown_provider() -> None:
    with pytest.raises(Unauthorized):
        verify("bitbucket", {}, b"body", _SECRET)

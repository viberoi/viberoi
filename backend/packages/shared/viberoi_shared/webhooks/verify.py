"""Webhook HMAC verification — per-provider.

Each provider has its own scheme:

  GitHub  — `X-Hub-Signature-256: sha256=<hex>`  HMAC-SHA256 over raw body
  GitLab  — `X-Gitlab-Token: <secret>`            constant-time token compare
  Linear  — `Linear-Signature: <hex>`             HMAC-SHA256 over raw body

The `raw_body` MUST be the exact bytes received (do not parse JSON first;
canonicalisation changes whitespace and breaks HMAC).

The caller passes the per-provider `secret` (bytes). The webhook Lambda
looks it up from `integration_oauth_tokens` and decrypts via
`viberoi_shared.crypto.envelope` before calling verify().
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable, Mapping

from viberoi_shared.errors import Unauthorized

# Provider names (string keys, not StrEnum, because they appear in
# webhook URLs and we want forward-compat with `bitbucket`, `azure_devops`,
# `jira` etc. without touching code).
GITHUB = "github"
GITLAB = "gitlab"
LINEAR = "linear"


def _get_header_case_insensitive(headers: Mapping[str, str], name: str) -> str:
    """Look up a header value, ignoring case."""
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return ""


def _hmac_sha256_hex(secret: bytes, body: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def verify_github(headers: Mapping[str, str], raw_body: bytes, secret: bytes) -> None:
    """Verify GitHub's `X-Hub-Signature-256`. Raises Unauthorized on mismatch."""
    sig_header = _get_header_case_insensitive(headers, "X-Hub-Signature-256")
    if not sig_header.lower().startswith("sha256="):
        raise Unauthorized
    submitted = sig_header[7:]
    expected = _hmac_sha256_hex(secret, raw_body)
    if not hmac.compare_digest(submitted, expected):
        raise Unauthorized


def verify_gitlab(headers: Mapping[str, str], raw_body: bytes, secret: bytes) -> None:  # noqa: ARG001
    """Verify GitLab's `X-Gitlab-Token`. Constant-time compare.

    GitLab transmits the secret directly as the token (not an HMAC), so the
    `raw_body` is unused here — the secret is treated as a bearer token.
    """
    submitted = _get_header_case_insensitive(headers, "X-Gitlab-Token")
    if not submitted:
        raise Unauthorized
    if not hmac.compare_digest(submitted.encode("utf-8"), secret):
        raise Unauthorized


def verify_linear(headers: Mapping[str, str], raw_body: bytes, secret: bytes) -> None:
    """Verify Linear's `Linear-Signature` HMAC-SHA256."""
    submitted = _get_header_case_insensitive(headers, "Linear-Signature")
    if not submitted:
        raise Unauthorized
    expected = _hmac_sha256_hex(secret, raw_body)
    if not hmac.compare_digest(submitted, expected):
        raise Unauthorized


_VERIFIERS: dict[str, Callable[[Mapping[str, str], bytes, bytes], None]] = {
    GITHUB: verify_github,
    GITLAB: verify_gitlab,
    LINEAR: verify_linear,
}


def verify(
    provider: str,
    headers: Mapping[str, str],
    raw_body: bytes,
    secret: bytes,
) -> None:
    """Dispatch to the right per-provider verifier.

    Raises `Unauthorized` for unknown providers, missing/invalid headers,
    or signature mismatch.
    """
    verifier = _VERIFIERS.get(provider.lower())
    if verifier is None:
        raise Unauthorized
    verifier(headers, raw_body, secret)

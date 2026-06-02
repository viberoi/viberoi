"""Webhook HMAC verification — per-provider.

Verified against current vendor docs 2026-06-03.

Each provider has its own scheme:

  GitHub  — `X-Hub-Signature-256: sha256=<hex>` HMAC-SHA256(secret, raw_body)
            https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries

  GitLab  — Two paths during the Standard-Webhooks migration:
            (a) NEW (preferred): `webhook-id`, `webhook-timestamp`,
                `webhook-signature: v1,<base64>` headers.
                signature = base64(HMAC-SHA256(secret, f"{id}.{ts}.{body}"))
                Timestamp tolerance 300 s for replay protection.
            (b) LEGACY: `X-Gitlab-Token: <secret>` bearer compare.
            verify_gitlab() accepts either; HMAC wins when both present.

  Linear  — `Linear-Signature: <hex>` HMAC-SHA256(secret, raw_body)

The `raw_body` MUST be the exact bytes received (do not parse JSON first;
canonicalisation changes whitespace and breaks HMAC).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from collections.abc import Callable, Mapping

from viberoi_shared.errors import Unauthorized

# Provider identifiers — string keys (not StrEnum) so adding bitbucket /
# azure_devops / jira later doesn't touch the dispatcher contract.
GITHUB = "github"
GITLAB = "gitlab"
LINEAR = "linear"

# Standard Webhooks replay window — reject deliveries whose `webhook-timestamp`
# differs from server time by more than this many seconds.
GITLAB_TIMESTAMP_TOLERANCE_S = 300


def _get_header_case_insensitive(headers: Mapping[str, str], name: str) -> str:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return ""


def _hmac_sha256_hex(secret: bytes, body: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def _hmac_sha256_b64(secret: bytes, body: bytes) -> str:
    return base64.b64encode(hmac.new(secret, body, hashlib.sha256).digest()).decode(
        "ascii"
    )


# ── GitHub ──────────────────────────────────────────────────────────────────


def verify_github(headers: Mapping[str, str], raw_body: bytes, secret: bytes) -> None:
    """Verify GitHub's `X-Hub-Signature-256`. Ignores the legacy SHA-1 header."""
    sig_header = _get_header_case_insensitive(headers, "X-Hub-Signature-256")
    if not sig_header.lower().startswith("sha256="):
        raise Unauthorized
    submitted = sig_header[7:]
    expected = _hmac_sha256_hex(secret, raw_body)
    if not hmac.compare_digest(submitted, expected):
        raise Unauthorized


# ── GitLab ──────────────────────────────────────────────────────────────────


def _verify_gitlab_standard_webhooks(
    headers: Mapping[str, str], raw_body: bytes, secret: bytes
) -> bool:
    """Try the new Standard-Webhooks HMAC scheme. Returns False if headers
    aren't present (let caller fall back to legacy)."""
    webhook_id = _get_header_case_insensitive(headers, "webhook-id")
    webhook_ts = _get_header_case_insensitive(headers, "webhook-timestamp")
    sig_header = _get_header_case_insensitive(headers, "webhook-signature")
    if not (webhook_id and webhook_ts and sig_header):
        return False

    # Replay protection: timestamp must be within tolerance window.
    try:
        delivered_ts = int(webhook_ts)
    except ValueError as e:
        raise Unauthorized from e
    if abs(time.time() - delivered_ts) > GITLAB_TIMESTAMP_TOLERANCE_S:
        raise Unauthorized

    signed_payload = f"{webhook_id}.{webhook_ts}.".encode() + raw_body
    expected_b64 = _hmac_sha256_b64(secret, signed_payload)

    # `webhook-signature` may carry multiple tokens for rotation, e.g.
    #   "v1,abc==  v1,def=="
    # Any match passes.
    for token in sig_header.split():
        if not token.startswith("v1,"):
            continue
        submitted = token[3:]
        if hmac.compare_digest(submitted, expected_b64):
            return True
    raise Unauthorized


def _verify_gitlab_legacy_bearer(
    headers: Mapping[str, str], secret: bytes
) -> bool:
    """Legacy `X-Gitlab-Token` bearer compare. False if header absent."""
    submitted = _get_header_case_insensitive(headers, "X-Gitlab-Token")
    if not submitted:
        return False
    if not hmac.compare_digest(submitted.encode("utf-8"), secret):
        raise Unauthorized
    return True


def verify_gitlab(headers: Mapping[str, str], raw_body: bytes, secret: bytes) -> None:
    """Verify a GitLab webhook. Accepts the new Standard-Webhooks HMAC scheme,
    falls back to legacy `X-Gitlab-Token` bearer compare during migration.

    Customers configure ONE secret per webhook; the verifier picks the right
    scheme based on which headers GitLab sends.
    """
    if _verify_gitlab_standard_webhooks(headers, raw_body, secret):
        return
    if _verify_gitlab_legacy_bearer(headers, secret):
        return
    raise Unauthorized


# ── Linear ──────────────────────────────────────────────────────────────────


def verify_linear(headers: Mapping[str, str], raw_body: bytes, secret: bytes) -> None:
    """Verify Linear's `Linear-Signature` HMAC-SHA256."""
    submitted = _get_header_case_insensitive(headers, "Linear-Signature")
    if not submitted:
        raise Unauthorized
    expected = _hmac_sha256_hex(secret, raw_body)
    if not hmac.compare_digest(submitted, expected):
        raise Unauthorized


# ── Dispatch + delivery-id helpers ──────────────────────────────────────────


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
    """Dispatch to the per-provider verifier. Raises `Unauthorized` on any
    failure, including unknown provider (no information leak)."""
    verifier = _VERIFIERS.get(provider.lower())
    if verifier is None:
        raise Unauthorized
    verifier(headers, raw_body, secret)


def extract_delivery_id(provider: str, headers: Mapping[str, str]) -> str | None:
    """Return the provider's per-delivery unique ID for SQS deduplication.

    Returns None when the provider doesn't expose one (Linear). In that case
    the Worker falls back to its native idempotency via the
    `sessions UNIQUE(org_id, session_id)` and the tickets/sprints upserts.
    """
    p = provider.lower()
    if p == GITHUB:
        return _get_header_case_insensitive(headers, "X-GitHub-Delivery") or None
    if p == GITLAB:
        # Standard Webhooks → webhook-id. Legacy → no delivery ID.
        return _get_header_case_insensitive(headers, "webhook-id") or None
    if p == LINEAR:
        # Linear doesn't document a delivery ID header (verified 2026-06-03).
        return None
    return None

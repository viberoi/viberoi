"""AWS Lambda entrypoint — `webhook_receiver.handler.handler`.

API Gateway HTTP API v2 → Lambda → SQS webhook_events.

The handler is sync (Lambda runtime requirement); a single `asyncio.run()`
bridges to the async shared library.
"""

from __future__ import annotations

import asyncio
import base64
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from viberoi_shared.errors import Unauthorized
from viberoi_shared.lambda_auth import verify as lambda_auth_verify
from viberoi_shared.logging import bind_request_context, configure_logging, get_logger
from viberoi_shared.sqs import publish as sqs_publish
from viberoi_shared.webhooks import extract_delivery_id, verify as verify_signature

from webhook_receiver.app.lookup import get_webhook_credentials

logger = get_logger(__name__)

# Configure structlog once per cold start.
configure_logging()

# Path pattern: /webhooks/{provider}/{integration_id}
_PATH_RE = re.compile(
    r"^/webhooks/(?P<provider>github|gitlab|linear)/(?P<integration_id>[0-9a-f-]{36})/?$"
)

# Headers we forward to SQS for the Worker — keep the set tight so the
# message doesn't bloat with unrelated headers (CloudFront, etc.).
_FORWARDED_HEADERS_BY_PROVIDER: dict[str, set[str]] = {
    "github": {
        "x-github-event",
        "x-github-delivery",
        "x-github-hook-id",
        "user-agent",
    },
    "gitlab": {
        "x-gitlab-event",
        "webhook-id",
        "webhook-timestamp",
        "user-agent",
    },
    "linear": {
        "linear-event",
        "linear-delivery",
        "user-agent",
    },
}

SQS_QUEUE = "webhook_events"


def _response(status: int, body: str = "ok") -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "text/plain"},
        "body": body,
    }


def _filter_headers(headers: dict[str, str], provider: str) -> dict[str, str]:
    allowed = _FORWARDED_HEADERS_BY_PROVIDER.get(provider, set())
    return {k: v for k, v in headers.items() if k.lower() in allowed}


def _extract_raw_body(event: dict[str, Any]) -> bytes:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body)
    return body.encode("utf-8") if isinstance(body, str) else bytes(body)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    bind_request_context(
        request_id=getattr(context, "aws_request_id", "lambda") if context else "lambda"
    )
    try:
        return asyncio.run(_async_handler(event, context))
    except Exception:  # noqa: BLE001
        # Don't leak details — the provider sees a generic 500 and retries.
        logger.exception("webhook_handler_unhandled")
        return _response(500, "internal error")


async def _async_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # ── Step 1: API Gateway shape sanity check ─────────────────────────────
    # We don't know the provider yet, so pass "webhook:?" — _verify_webhook
    # only inspects event shape, not the provider suffix.
    try:
        lambda_auth_verify(event, context, expected_source="webhook:unknown")
    except Unauthorized:
        return _response(401, "unauthorized")

    # ── Step 2: parse path ─────────────────────────────────────────────────
    path = event.get("rawPath", "") or event.get("requestContext", {}).get(
        "http", {}
    ).get("path", "")
    match = _PATH_RE.match(path)
    if not match:
        return _response(404, "not found")
    provider = match.group("provider")
    integration_id_str = match.group("integration_id")
    try:
        integration_id = UUID(integration_id_str)
    except ValueError:
        return _response(404, "not found")

    bind_request_context(
        request_id=getattr(context, "aws_request_id", "lambda") if context else "lambda"
    )
    logger.info(
        "webhook_received",
        provider=provider,
        integration_id=integration_id_str,
    )

    # ── Step 3: raw body ───────────────────────────────────────────────────
    raw_body = _extract_raw_body(event)
    headers = event.get("headers") or {}

    # ── Step 4: load org + decrypted secret ────────────────────────────────
    creds = await get_webhook_credentials(integration_id, provider)
    if creds is None:
        return _response(404, "not found")
    org_id, secret = creds

    # ── Step 5: HMAC verify ────────────────────────────────────────────────
    try:
        verify_signature(provider, headers, raw_body, secret)
    except Unauthorized:
        logger.warning(
            "webhook_signature_mismatch",
            provider=provider,
            integration_id=integration_id_str,
        )
        return _response(401, "unauthorized")

    # ── Step 6: delivery id (best-effort dedup key) ────────────────────────
    delivery_id = extract_delivery_id(provider, headers)

    # ── Step 7: publish raw payload to SQS ─────────────────────────────────
    forwarded_headers = _filter_headers(headers, provider)
    await sqs_publish(
        SQS_QUEUE,
        {
            "org_id": str(org_id),
            "provider": provider,
            "delivery_id": delivery_id,
            "headers": forwarded_headers,
            "body_b64": base64.b64encode(raw_body).decode("ascii"),
            "received_at": datetime.now(tz=UTC).isoformat(),
        },
        deduplication_id=delivery_id,
    )

    logger.info(
        "webhook_published",
        provider=provider,
        integration_id=integration_id_str,
        org_id=str(org_id),
        delivery_id=delivery_id,
    )
    return _response(200, "ok")

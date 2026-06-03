"""Slack incoming-webhook delivery.

`POST {webhook_url}` with `{text, blocks}`. Outcome is a typed
DeliveryResult so the consumer can act on transient vs permanent
failures distinctly.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import orjson

from notification.app.templates import SlackPayload
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)

REQUEST_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class DeliveryResult:
    """Outcome of one webhook attempt.

    `ok=True` → ack.
    `ok=False, permanent=True` → ack + disable channel (URL is bad).
    `ok=False, permanent=False` → don't ack (SQS retries; circuit
                                   breaker may open).
    """

    ok: bool
    permanent: bool
    status_code: int | None = None


async def deliver(*, webhook_url: str, payload: SlackPayload) -> DeliveryResult:
    body = orjson.dumps({"text": payload.text, "blocks": payload.blocks})
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                webhook_url,
                content=body,
                headers={"Content-Type": "application/json"},
            )
    except httpx.HTTPError as e:
        logger.warning(
            "slack_delivery_transport_error", error_type=type(e).__name__
        )
        return DeliveryResult(ok=False, permanent=False)

    if response.status_code == 200:
        return DeliveryResult(ok=True, permanent=False, status_code=200)
    if response.status_code == 429 or 500 <= response.status_code < 600:
        # Transient — retry.
        return DeliveryResult(
            ok=False, permanent=False, status_code=response.status_code
        )
    # 4xx (404 no_service, 403 invalid_token, etc.) — URL is broken or
    # revoked; retrying won't help.
    return DeliveryResult(
        ok=False, permanent=True, status_code=response.status_code
    )

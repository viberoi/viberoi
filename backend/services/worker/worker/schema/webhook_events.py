"""Webhook event envelope from the webhook_receiver Lambda.

The Lambda HMAC-verifies inbound provider webhooks, then publishes a
JSON envelope to SQS `webhook_events`. This module defines the shape;
the worker's webhook_processor consumes it.

Envelope shape (per webhook_receiver/CLAUDE.md step 7):
    {
      "org_id": "uuid-str",
      "provider": "github" | "gitlab" | "linear",
      "delivery_id": "provider-delivery-id",
      "headers": { filtered subset },
      "body_b64": "base64(raw bytes)",
      "received_at": "iso8601",
    }

We base64-decode body on this side to keep the SQS payload small for
binary-ish providers and to dodge SQS's 256 KB string limit for
large diffs.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class WebhookEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    org_id: str
    provider: str
    delivery_id: str
    headers: dict[str, str] = {}
    body_b64: str
    received_at: datetime

    def event_type(self) -> str | None:
        """Provider-specific event-type header.

        GitHub: X-GitHub-Event (e.g. "pull_request", "push")
        Linear: X-Linear-Event
        GitLab: X-Gitlab-Event
        """
        if self.provider == "github":
            return _h(self.headers, "x-github-event")
        if self.provider == "linear":
            return _h(self.headers, "x-linear-event")
        if self.provider == "gitlab":
            return _h(self.headers, "x-gitlab-event")
        return None

    def decoded_body(self) -> bytes:
        import base64

        return base64.b64decode(self.body_b64)

    def parsed_body(self) -> dict[str, Any]:
        import orjson

        return orjson.loads(self.decoded_body())


def _h(headers: dict[str, str], name: str) -> str | None:
    """Header lookup that's case-insensitive — API Gateway normalises
    inbound names to lowercase but some providers send mixed case."""
    target = name.lower()
    for k, v in headers.items():
        if k.lower() == target:
            return v
    return None

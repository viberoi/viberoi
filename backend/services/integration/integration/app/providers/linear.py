"""Linear OAuth 2.0 provider adapter.

Docs verified 2026-06-03:
- OAuth: https://linear.app/developers/oauth-2-0-authentication
- GraphQL: https://linear.app/developers/graphql
- Webhooks: https://linear.app/developers/webhooks
- Rate limits: https://linear.app/developers/rate-limiting

Important corrections caught during doc verification:
- Access tokens are **24 hours**, not "~10 years" as some older sources
  claim. MUST implement refresh-token flow.
- `actor=application` is deprecated → use `actor=app`.
- Linear sends `Linear-Delivery` + `Linear-Event` headers (used by
  viberoi_shared.webhooks.extract_delivery_id for SQS dedup).
- Webhook body includes `webhookTimestamp` (ms) — Worker validates ≤60 s
  for replay protection (not done here, since this adapter doesn't see
  inbound webhooks).
- Rate limits: 5,000 req/h + 2,000,000 complexity/h per OAuth app.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import orjson

from integration.app.http_client import request as http_request
from integration.app.providers.base import (
    OAuthCallbackError,
    ProviderAdapter,
    ProviderConnection,
    TokenRefreshError,
    WebhookRegistration,
    WebhookRegistrationError,
)
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)

AUTHORIZE_URL = "https://linear.app/oauth/authorize"
TOKEN_URL = "https://api.linear.app/oauth/token"  # noqa: S105
REVOKE_URL = "https://api.linear.app/oauth/revoke"  # noqa: S105
GRAPHQL_URL = "https://api.linear.app/graphql"

# Read-only over issues, cycles, projects, teams, users.
DEFAULT_SCOPE = "read"
WEBHOOK_RESOURCE_TYPES = ["Issue", "Cycle", "Project"]


class LinearAdapter(ProviderAdapter):
    name = "linear"

    def __init__(self, *, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    # ── Authorization ──────────────────────────────────────────────────────

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": DEFAULT_SCOPE,
            "state": state,
            # `actor=app` (not deprecated `actor=application`) — API calls run
            # as the integration itself, not on behalf of the installer.
            "actor": "app",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    async def complete_callback(
        self,
        params: Mapping[str, str],
        *,
        redirect_uri: str,
    ) -> ProviderConnection:
        code = params.get("code")
        if not code:
            raise OAuthCallbackError(
                "Linear callback missing code — user may have denied access."
            )
        return await self._exchange("authorization_code", code=code, redirect_uri=redirect_uri)

    async def refresh(self, connection: ProviderConnection) -> ProviderConnection:
        if not connection.refresh_token:
            raise TokenRefreshError(
                "Linear connection has no refresh token; user must re-connect."
            )
        return await self._exchange(
            "refresh_token", refresh_token=connection.refresh_token
        )

    async def _exchange(self, grant_type: str, **fields: str) -> ProviderConnection:
        body = {
            "grant_type": grant_type,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            **fields,
        }
        response = await http_request(
            "POST",
            TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            content=urlencode(body).encode("utf-8"),
        )
        if response.status_code >= 400:
            logger.warning(
                "linear_token_exchange_failed",
                grant_type=grant_type,
                status=response.status_code,
            )
            raise TokenRefreshError(
                f"Linear token endpoint returned {response.status_code}."
            )
        data = response.json()
        expires_at: datetime | None = None
        if "expires_in" in data:
            # `expires_in` is seconds (24h = 86400). Add to current time.
            expires_at = datetime.now(tz=UTC) + timedelta(seconds=int(data["expires_in"]))
        return ProviderConnection(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            scope=data.get("scope"),
            installation_id=None,
            extra={"token_type": data.get("token_type", "Bearer")},
        )

    # ── Post-auth discovery ────────────────────────────────────────────────

    async def discover(self, connection: ProviderConnection) -> dict:
        """Run the standard viewer + organization + teams query."""
        query = """
        query {
          viewer { id name }
          organization { id name urlKey }
          teams(first: 250) { nodes { id key name } }
        }
        """
        return await self.graphql(connection.access_token, query)

    async def graphql(
        self,
        access_token: str,
        query: str,
        variables: Mapping[str, object] | None = None,
    ) -> dict:
        """Run a GraphQL query and return the parsed JSON (caller handles the data field)."""
        body: dict[str, object] = {"query": query}
        if variables:
            body["variables"] = dict(variables)
        response = await http_request(
            "POST",
            GRAPHQL_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            content=orjson.dumps(body),
        )
        if response.status_code >= 400:
            raise TokenRefreshError(
                f"Linear GraphQL returned {response.status_code}."
            )
        return response.json()

    # ── Webhook registration ───────────────────────────────────────────────

    async def register_webhook(
        self,
        connection: ProviderConnection,
        *,
        webhook_url: str,
        secret: str,
    ) -> WebhookRegistration:
        """Create a single Linear webhook subscribed to Issue/Cycle/Project."""
        mutation = """
        mutation CreateWebhook($input: WebhookCreateInput!) {
          webhookCreate(input: $input) {
            success
            webhook { id }
          }
        }
        """
        variables = {
            "input": {
                "url": webhook_url,
                "resourceTypes": WEBHOOK_RESOURCE_TYPES,
                "secret": secret,
                "allPublicTeams": True,
                "enabled": True,
                "label": "VibeROI",
            }
        }
        result = await self.graphql(connection.access_token, mutation, variables)
        payload = (result.get("data") or {}).get("webhookCreate") or {}
        if not payload.get("success") or not payload.get("webhook"):
            logger.warning(
                "linear_webhook_create_failed",
                response=result,
            )
            raise WebhookRegistrationError(
                "Linear webhookCreate did not return success."
            )
        webhook_id = str(payload["webhook"]["id"])
        return WebhookRegistration(
            provider_webhook_ids=[webhook_id], secret=secret
        )

    # ── Revoke ─────────────────────────────────────────────────────────────

    async def revoke(self, connection: ProviderConnection) -> None:
        """Best-effort: revoke the OAuth token. Webhook cleanup is a separate
        call the orchestrator makes using stored webhook ids."""
        try:
            await http_request(
                "POST",
                REVOKE_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                content=urlencode(
                    {
                        "token": connection.access_token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    }
                ).encode("utf-8"),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("linear_revoke_failed", error=str(e))

    async def delete_webhook(
        self, connection: ProviderConnection, webhook_id: str
    ) -> None:
        """Delete a webhook by ID (called per-webhook from the orchestrator)."""
        mutation = """
        mutation DeleteWebhook($id: String!) {
          webhookDelete(id: $id) { success }
        }
        """
        try:
            await self.graphql(connection.access_token, mutation, {"id": webhook_id})
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "linear_webhook_delete_failed", webhook_id=webhook_id, error=str(e)
            )


def _epoch_to_dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)


def _now_epoch() -> float:
    return time.time()

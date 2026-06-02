"""Jira (Atlassian Cloud) OAuth 2.0 3LO provider adapter.

Docs verified 2026-06-03:
- OAuth: https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/
- Webhooks: https://developer.atlassian.com/cloud/jira/platform/webhooks/
- REST API (issues): https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/
- Agile API (boards/sprints): https://developer.atlassian.com/cloud/jira/software/rest/

Important corrections caught during doc verification:
- Refresh tokens are **90 days** (not 365), still rotate on every use.
- OAuth 2.0 webhooks (created via `/rest/api/3/webhook`) use **bearer-token
  authentication, NOT HMAC**. Jira injects our OAuth app's bearer token
  in the inbound webhook's `Authorization` header. Slice 4 V1 accepts
  URL-secrecy via the per-integration UUID in the path; layered bearer
  verification deferred to a hardening pass.
- Webhooks **expire after 30 days** and must be refreshed via
  `PUT /rest/api/3/webhook/refresh`. A cron job (Slice 5+) refreshes them.
- OAuth 2.0 webhook limit: 5 webhooks per app per user per tenant.
- The new token-paginated search (`POST /search/jql`) has community-reported
  pagination bugs; Slice 4 sync code (C5) sticks with the legacy
  `GET /rest/api/3/search?startAt=...` until upstream is stable.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import orjson

from integration.app.http_client import request as http_request
from integration.app.providers.base import (
    OAuthCallbackError,
    ProviderAdapter,
    ProviderConnection,
    ProviderError,
    TokenRefreshError,
    WebhookRegistration,
    WebhookRegistrationError,
)
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)

AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"  # noqa: S105
ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
API_BASE = "https://api.atlassian.com/ex/jira"

# `offline_access` is mandatory for refresh tokens. `read:jira-user` is needed
# to dereference issue.assignee. `read:jira-work` covers issues/sprints/boards.
DEFAULT_SCOPES = "read:jira-work read:jira-user offline_access"

WEBHOOK_EVENTS = [
    "jira:issue_created",
    "jira:issue_updated",
    "sprint_started",
    "sprint_closed",
]


class JiraAdapter(ProviderAdapter):
    name = "jira"

    def __init__(self, *, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    # ── Authorization ──────────────────────────────────────────────────────

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        params = {
            "audience": "api.atlassian.com",
            "client_id": self._client_id,
            "scope": DEFAULT_SCOPES,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
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
                "Jira callback missing code — user may have denied consent."
            )
        connection = await self._exchange(
            "authorization_code", code=code, redirect_uri=redirect_uri
        )
        # Discovery: cloud_id (mandatory for any subsequent API call) +
        # the sprint custom-field id (varies per Jira tenant).
        cloud_id = await self._discover_cloud_id(connection.access_token)
        sprint_field_id = await self._discover_sprint_field_id(
            connection.access_token, cloud_id
        )
        return ProviderConnection(
            access_token=connection.access_token,
            refresh_token=connection.refresh_token,
            expires_at=connection.expires_at,
            scope=connection.scope,
            installation_id=None,
            extra={"cloud_id": cloud_id, "sprint_field_id": sprint_field_id},
        )

    async def refresh(self, connection: ProviderConnection) -> ProviderConnection:
        if not connection.refresh_token:
            raise TokenRefreshError(
                "Jira connection has no refresh token; user must re-connect."
            )
        new = await self._exchange(
            "refresh_token", refresh_token=connection.refresh_token
        )
        # Preserve the discovery metadata across refresh.
        return ProviderConnection(
            access_token=new.access_token,
            refresh_token=new.refresh_token,
            expires_at=new.expires_at,
            scope=new.scope,
            installation_id=None,
            extra=connection.extra,
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
                "jira_token_exchange_failed",
                grant_type=grant_type,
                status=response.status_code,
            )
            raise TokenRefreshError(
                f"Jira token endpoint returned {response.status_code}."
            )
        data = response.json()
        expires_at: datetime | None = None
        if "expires_in" in data:
            expires_at = datetime.now(tz=UTC) + timedelta(seconds=int(data["expires_in"]))
        return ProviderConnection(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            scope=data.get("scope"),
            installation_id=None,
            extra={},
        )

    # ── Discovery ──────────────────────────────────────────────────────────

    async def _discover_cloud_id(self, access_token: str) -> str:
        response = await http_request(
            "GET",
            ACCESSIBLE_RESOURCES_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        if response.status_code >= 400:
            raise ProviderError(
                f"Jira accessible-resources returned {response.status_code}."
            )
        resources = response.json()
        if not resources:
            raise ProviderError(
                "Jira returned no accessible resources for the authorized user."
            )
        # The user may have access to multiple sites; the first is typically the
        # one they consented to. Surface as discovery metadata; the orchestrator
        # can prompt for a choice if more than one exists (V2).
        return str(resources[0]["id"])

    async def _discover_sprint_field_id(
        self, access_token: str, cloud_id: str
    ) -> str | None:
        response = await http_request(
            "GET",
            f"{API_BASE}/{cloud_id}/rest/api/3/field",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        if response.status_code >= 400:
            logger.warning(
                "jira_field_discovery_failed", status=response.status_code
            )
            return None
        for field in response.json():
            if field.get("name") == "Sprint" and field.get("custom"):
                return str(field["id"])
        return None

    # ── Webhook registration ───────────────────────────────────────────────

    async def register_webhook(
        self,
        connection: ProviderConnection,
        *,
        webhook_url: str,
        secret: str,  # noqa: ARG002 — Jira OAuth 2.0 webhooks don't accept a secret
    ) -> WebhookRegistration:
        """Register a Jira OAuth 2.0 webhook.

        Jira does NOT accept a webhook signing secret (the OAuth 2.0
        flavor uses bearer-token auth on delivery instead). The `secret`
        parameter is accepted to match the ProviderAdapter contract but
        discarded — see CLAUDE.md for the Slice 4 security trade-off.
        """
        cloud_id = connection.extra.get("cloud_id")
        if not cloud_id:
            raise WebhookRegistrationError(
                "Cannot register Jira webhook without cloud_id (discovery failed)."
            )
        response = await http_request(
            "POST",
            f"{API_BASE}/{cloud_id}/rest/api/3/webhook",
            headers={
                "Authorization": f"Bearer {connection.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            content=orjson.dumps(
                {
                    "url": webhook_url,
                    "webhooks": [
                        {
                            "events": WEBHOOK_EVENTS,
                            "jqlFilter": "project is not EMPTY",
                        }
                    ],
                }
            ),
        )
        if response.status_code >= 400:
            raise WebhookRegistrationError(
                f"Jira webhook create returned {response.status_code}."
            )
        data = response.json()
        # Response shape: {webhookRegistrationResult: [{createdWebhookId, errors}]}
        results = data.get("webhookRegistrationResult", [])
        webhook_ids: list[str] = []
        for entry in results:
            if entry.get("createdWebhookId"):
                webhook_ids.append(str(entry["createdWebhookId"]))
            elif entry.get("errors"):
                logger.warning("jira_webhook_partial_failure", errors=entry["errors"])
        if not webhook_ids:
            raise WebhookRegistrationError(
                "Jira webhook create returned no createdWebhookId entries."
            )
        # Empty string for `secret` documents that no HMAC secret is used for
        # Jira; the storage layer skips writing the column when this is "".
        return WebhookRegistration(provider_webhook_ids=webhook_ids, secret="")

    async def refresh_webhooks(
        self, connection: ProviderConnection, webhook_ids: list[str]
    ) -> None:
        """Reset the 30-day expiry on the registered webhooks.

        Called by a cron job (Slice 5+) before the deadline.
        """
        cloud_id = connection.extra.get("cloud_id")
        if not cloud_id:
            return
        await http_request(
            "PUT",
            f"{API_BASE}/{cloud_id}/rest/api/3/webhook/refresh",
            headers={
                "Authorization": f"Bearer {connection.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            content=orjson.dumps({"webhookIds": [int(w) for w in webhook_ids]}),
        )

    # ── Revoke ─────────────────────────────────────────────────────────────

    async def revoke(self, connection: ProviderConnection) -> None:
        """Best-effort: delete all webhooks registered for this connection.

        Atlassian doesn't expose an OAuth-token revoke endpoint (the
        user revokes via the Atlassian account settings). We clean up
        webhooks so Jira stops trying to deliver to us.
        """
        cloud_id = connection.extra.get("cloud_id")
        webhook_ids = connection.extra.get("webhook_ids", [])
        if not cloud_id or not webhook_ids:
            return
        try:
            await http_request(
                "DELETE",
                f"{API_BASE}/{cloud_id}/rest/api/3/webhook",
                headers={
                    "Authorization": f"Bearer {connection.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                content=orjson.dumps(
                    {"webhookIds": [int(w) for w in webhook_ids]}
                ),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("jira_revoke_failed", error=str(e))

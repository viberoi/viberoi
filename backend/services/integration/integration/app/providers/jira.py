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
from uuid import UUID

import orjson

from integration.app.http_client import request as http_request
from integration.app.providers.base import (
    OAuthCallbackError,
    ProviderAdapter,
    ProviderConnection,
    ProviderError,
    SyncResult,
    TokenRefreshError,
    WebhookRegistration,
    WebhookRegistrationError,
)
from viberoi_shared.db import org_scoped_session
from viberoi_shared.logging import get_logger
from viberoi_shared.tickets import upsert_sprint, upsert_ticket

logger = get_logger(__name__)

AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"  # noqa: S105
ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
API_BASE = "https://api.atlassian.com/ex/jira"

# `offline_access` is mandatory for refresh tokens. `read:jira-user` is needed
# to dereference issue.assignee. `read:jira-work` covers issues/sprints/boards.
DEFAULT_SCOPES = "read:jira-work read:jira-user offline_access"

HTTP_ERROR_FLOOR = 400

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
        if response.status_code >= HTTP_ERROR_FLOOR:
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
        if response.status_code >= HTTP_ERROR_FLOOR:
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
        if response.status_code >= HTTP_ERROR_FLOOR:
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
        if response.status_code >= HTTP_ERROR_FLOOR:
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

    # ── Sync ───────────────────────────────────────────────────────────────

    async def sync(
        self,
        connection: ProviderConnection,
        *,
        org_id: UUID,
        since: datetime | None,
    ) -> SyncResult:
        """V1: fetch board sprints + recent issues for the discovered cloud_id.

        - sprints: paginate `GET /rest/agile/1.0/board/{boardId}/sprint`
          (limited to the first board for V1 — multi-board fan-out is V2).
        - tickets: `POST /rest/api/3/search/jql` JQL `updated >= "since"`,
          page until exhausted or `MAX_TICKETS` reached.
        - system: `jira`.
        - external_id: the issue key (e.g. `ABC-123`).
        """
        if since is None:
            since = datetime.now(tz=UTC) - timedelta(days=90)
        cloud_id = connection.extra.get("cloud_id")
        if not cloud_id:
            return SyncResult(errors=["jira sync: cloud_id missing from connection"])

        sprints = 0
        tickets = 0
        errors: list[str] = []

        try:
            sprints += await self._sync_sprints(connection, cloud_id, org_id)
        except Exception as e:
            errors.append(f"jira sprints: {e}")

        try:
            tickets += await self._sync_tickets(connection, cloud_id, org_id, since)
        except Exception as e:
            errors.append(f"jira tickets: {e}")

        return SyncResult(
            tickets_upserted=tickets, sprints_upserted=sprints, errors=errors
        )

    async def _sync_sprints(
        self,
        connection: ProviderConnection,
        cloud_id: str,
        org_id: UUID,
    ) -> int:
        """Fetch sprints from the first board only (V1)."""
        boards_resp = await http_request(
            "GET",
            f"{API_BASE}/{cloud_id}/rest/agile/1.0/board",
            headers={
                "Authorization": f"Bearer {connection.access_token}",
                "Accept": "application/json",
            },
            params={"maxResults": 1},
        )
        if boards_resp.status_code >= HTTP_ERROR_FLOOR:
            return 0
        values = boards_resp.json().get("values", [])
        if not values:
            return 0
        board_id = str(values[0]["id"])

        sprints_resp = await http_request(
            "GET",
            f"{API_BASE}/{cloud_id}/rest/agile/1.0/board/{board_id}/sprint",
            headers={
                "Authorization": f"Bearer {connection.access_token}",
                "Accept": "application/json",
            },
            params={"maxResults": 50},
        )
        if sprints_resp.status_code >= HTTP_ERROR_FLOOR:
            return 0
        count = 0
        for sprint in sprints_resp.json().get("values", []):
            async with org_scoped_session(org_id) as db:
                await upsert_sprint(
                    db,
                    org_id=org_id,
                    system="jira",
                    external_id=str(sprint["id"]),
                    name=sprint["name"],
                    state=sprint.get("state", "future").lower(),
                    started_at=_parse_jira_timestamp(sprint.get("startDate")),
                    ended_at=_parse_jira_timestamp(sprint.get("endDate")),
                    completed_at=_parse_jira_timestamp(sprint.get("completeDate")),
                    board_id=board_id,
                )
            count += 1
        return count

    async def _sync_tickets(
        self,
        connection: ProviderConnection,
        cloud_id: str,
        org_id: UUID,
        since: datetime,
    ) -> int:
        """Page through legacy JQL issue search. Capped at MAX_TICKETS per run.

        Uses `GET /rest/api/3/search` rather than the new `POST /search/jql`
        per the file-level note about pagination bugs in the new endpoint.
        """
        jql = f'updated >= "{since.strftime("%Y-%m-%d %H:%M")}"'
        start_at = 0
        page_size = 100
        max_tickets = 500
        count = 0
        while count < max_tickets:
            resp = await http_request(
                "GET",
                f"{API_BASE}/{cloud_id}/rest/api/3/search",
                headers={
                    "Authorization": f"Bearer {connection.access_token}",
                    "Accept": "application/json",
                },
                params={
                    "jql": jql,
                    "fields": "summary,status,created,resolutiondate",
                    "startAt": start_at,
                    "maxResults": page_size,
                },
            )
            if resp.status_code >= HTTP_ERROR_FLOOR:
                break
            data = resp.json()
            issues = data.get("issues", [])
            if not issues:
                break
            for issue in issues:
                fields = issue.get("fields", {})
                created = _parse_jira_timestamp(fields.get("created"))
                if created is None:
                    continue
                resolved = _parse_jira_timestamp(fields.get("resolutiondate"))
                status_key = (
                    fields.get("status", {})
                    .get("statusCategory", {})
                    .get("key", "open")
                )
                async with org_scoped_session(org_id) as db:
                    await upsert_ticket(
                        db,
                        org_id=org_id,
                        system="jira",
                        external_id=issue["key"],
                        title=fields.get("summary", "")[:500],
                        status="closed" if resolved else status_key,
                        created_at_external=created,
                        closed_at_external=resolved,
                    )
                count += 1
                if count >= max_tickets:
                    break
            total = data.get("total", 0)
            start_at += len(issues)
            if start_at >= total:
                break
        return count

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
        except Exception as e:
            logger.warning("jira_revoke_failed", error=str(e))


def _parse_jira_timestamp(value: str | None) -> datetime | None:
    """Jira returns ISO 8601 with offset (e.g. `2026-06-01T10:00:00.000+0000`)."""
    if not value:
        return None
    # Normalize `+0000` (5-char suffix: sign + 4 digits) → `+00:00`.
    tz_suffix_len = 5
    if (
        len(value) >= tz_suffix_len
        and (value[-tz_suffix_len] in "+-")
        and ":" not in value[-tz_suffix_len:]
    ):
        value = value[:-tz_suffix_len] + value[-tz_suffix_len:-2] + ":" + value[-2:]
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError:
        return None

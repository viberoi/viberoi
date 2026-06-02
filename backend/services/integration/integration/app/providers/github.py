"""GitHub App provider adapter.

NOT classic OAuth — GitHub Apps issue short-lived installation access
tokens (1h) which we mint on demand from an App-level JWT signed with the
App's RSA private key.

Key docs (verified 2026-06-03):
- App JWT: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app
- Installation token: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app
- Webhooks: https://docs.github.com/en/rest/repos/webhooks

Notes from doc verification:
- `X-GitHub-Api-Version` is now `2026-03-10` (was `2022-11-28`).
- Installation tokens use the new stateless `ghs_APPID_JWT` format — no
  fixed length. Treat as opaque; never validate length.
- `iss` claim should be the App's Client ID (the `lv1_xxxx` form) per
  current docs; numeric App ID still accepted during the transition.
- App JWT max lifetime is 10 minutes (600 s); we use 9 minutes (540 s)
  to leave margin for clock drift.

Spoofing trade-off accepted for Slice 4 V1:
- After install, GitHub redirects to our setup URL with
  `?installation_id=...&state=...`. The `state` parameter ties the
  callback back to the (org_id, developer_id) that initiated the flow.
- An attacker who initiates the flow themselves CAN trick a victim's
  browser into completing the install against their own state — binding
  the victim's installation to the attacker's org. Mitigation V2: layer
  the user-authorization OAuth callback on top. V1 acceptance documented
  in CLAUDE.md.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import jwt  # PyJWT
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

API_VERSION = "2026-03-10"
ACCEPT = "application/vnd.github+json"
GITHUB_API_BASE = "https://api.github.com"
JWT_LIFETIME_SECONDS = 540  # 9 minutes — under the 10-minute cap
JWT_BACKDATE_SECONDS = 60  # 1 minute, per docs (clock-drift tolerance)


class GitHubAppAdapter(ProviderAdapter):
    name = "github"

    def __init__(
        self,
        *,
        app_id: str,
        app_slug: str,
        private_key_pem: str,
    ) -> None:
        """`app_id` may be the numeric App ID or the Client ID (`lv1_...`)."""
        self._app_id = app_id
        self._app_slug = app_slug
        self._private_key_pem = private_key_pem

    # ── Authorization ──────────────────────────────────────────────────────

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:  # noqa: ARG002
        """GitHub App install URL. `redirect_uri` is configured at the App
        level (Setup URL); we don't pass it here."""
        return f"https://github.com/apps/{self._app_slug}/installations/new?state={state}"

    async def complete_callback(
        self,
        params: Mapping[str, str],
        *,
        redirect_uri: str,  # noqa: ARG002
    ) -> ProviderConnection:
        installation_id = params.get("installation_id")
        if not installation_id:
            raise OAuthCallbackError(
                "GitHub callback missing installation_id — the customer may have "
                "denied the install."
            )
        # We don't trust this value at face value — it's read from the URL.
        # The state-binding check happens before us in the OAuth route.
        return await self._mint_installation_token(installation_id)

    async def refresh(self, connection: ProviderConnection) -> ProviderConnection:
        """GitHub installation tokens are minted, not refreshed. Re-mint
        using the persisted installation_id."""
        if not connection.installation_id:
            raise TokenRefreshError(
                "Cannot refresh GitHub connection without installation_id."
            )
        return await self._mint_installation_token(connection.installation_id)

    async def _mint_installation_token(self, installation_id: str) -> ProviderConnection:
        app_jwt = self._sign_app_jwt()
        response = await http_request(
            "POST",
            f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": ACCEPT,
                "X-GitHub-Api-Version": API_VERSION,
            },
        )
        if response.status_code >= 400:
            logger.warning(
                "github_installation_token_mint_failed",
                installation_id=installation_id,
                status=response.status_code,
            )
            raise TokenRefreshError(
                f"GitHub returned {response.status_code} on installation token mint."
            )
        data = response.json()
        expires_at = _parse_github_timestamp(data.get("expires_at"))
        return ProviderConnection(
            access_token=data["token"],
            refresh_token=None,  # GitHub installation tokens are re-minted
            expires_at=expires_at,
            scope=None,
            installation_id=installation_id,
            extra={
                "permissions": data.get("permissions"),
                "repository_selection": data.get("repository_selection"),
            },
        )

    def _sign_app_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iat": now - JWT_BACKDATE_SECONDS,
            "exp": now + JWT_LIFETIME_SECONDS,
            "iss": self._app_id,
        }
        return jwt.encode(payload, self._private_key_pem, algorithm="RS256")

    # ── Webhook registration ───────────────────────────────────────────────

    async def register_webhook(
        self,
        connection: ProviderConnection,
        *,
        webhook_url: str,
        secret: str,
    ) -> WebhookRegistration:
        """Register a webhook on every repo the installation granted.

        We use per-repo webhooks (not the App-level webhook) so each
        customer's URL carries their integration_id. See CLAUDE.md for
        the trade-off discussion.
        """
        repos = await self._list_installation_repos(connection.access_token)
        webhook_ids: list[str] = []
        for repo in repos:
            owner = repo["owner"]["login"]
            name = repo["name"]
            response = await http_request(
                "POST",
                f"{GITHUB_API_BASE}/repos/{owner}/{name}/hooks",
                headers={
                    "Authorization": f"Bearer {connection.access_token}",
                    "Accept": ACCEPT,
                    "X-GitHub-Api-Version": API_VERSION,
                },
                content=orjson.dumps(
                    {
                        "name": "web",
                        "active": True,
                        "events": ["push", "pull_request", "create", "delete", "issues"],
                        "config": {
                            "url": webhook_url,
                            "content_type": "json",
                            "secret": secret,
                            "insecure_ssl": "0",
                        },
                    }
                ),
            )
            if response.status_code not in (200, 201):
                logger.warning(
                    "github_webhook_create_failed",
                    repo=f"{owner}/{name}",
                    status=response.status_code,
                )
                # Keep going for the other repos; surface aggregate failure
                # via the count below.
                continue
            webhook_ids.append(f"{owner}/{name}:{response.json()['id']}")

        if not webhook_ids:
            raise WebhookRegistrationError(
                f"Failed to register a webhook on any of {len(repos)} repositories."
            )
        return WebhookRegistration(provider_webhook_ids=webhook_ids, secret=secret)

    async def _list_installation_repos(self, installation_token: str) -> list[dict[str, Any]]:
        """Paginate `GET /installation/repositories`."""
        repos: list[dict[str, Any]] = []
        page = 1
        while True:
            response = await http_request(
                "GET",
                f"{GITHUB_API_BASE}/installation/repositories",
                headers={
                    "Authorization": f"Bearer {installation_token}",
                    "Accept": ACCEPT,
                    "X-GitHub-Api-Version": API_VERSION,
                },
                params={"per_page": 100, "page": page},
            )
            if response.status_code >= 400:
                logger.warning(
                    "github_list_repos_failed",
                    status=response.status_code,
                    page=page,
                )
                break
            data = response.json()
            batch = data.get("repositories", [])
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return repos

    # ── Revoke ──────────────────────────────────────────────────────────────

    async def revoke(self, connection: ProviderConnection) -> None:
        """Best-effort revoke. Calls `DELETE /installation/token` to
        invalidate the current installation token immediately."""
        try:
            await http_request(
                "DELETE",
                f"{GITHUB_API_BASE}/installation/token",
                headers={
                    "Authorization": f"Bearer {connection.access_token}",
                    "Accept": ACCEPT,
                    "X-GitHub-Api-Version": API_VERSION,
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("github_revoke_failed", error=str(e))


def _parse_github_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    # GitHub returns RFC 3339 with `Z` suffix (e.g. "2026-06-03T12:34:56Z").
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(UTC)

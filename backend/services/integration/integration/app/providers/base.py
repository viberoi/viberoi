"""Provider-adapter interface — every provider implements this contract.

Design notes:
- `complete_callback` takes a dict of callback query parameters because
  providers disagree on what they send (GitHub: `installation_id` + maybe
  `code`; Jira/Linear: `code` only). The adapter picks what it needs.
- `refresh` accepts the existing `ProviderConnection` and returns a new
  one. For providers without refresh (Linear, GitHub installation tokens
  re-minted from App JWT), the adapter may produce a fresh connection
  without any inbound refresh token.
- `register_webhook` may register multiple webhooks (GitHub registers per
  repo); the result carries a list of provider-side webhook IDs so we
  can revoke them on disconnect.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ProviderConnection:
    """Tokens + metadata returned from a successful auth flow / refresh.

    Pass to `viberoi_shared.integrations.repository.store_token(...)` to
    persist (the repository encrypts via KMS envelope).
    """

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scope: str | None = None
    installation_id: str | None = None
    # Provider-specific bag: GitHub puts permissions/repository_selection here;
    # Jira puts cloud_id + sprint_field_id; Linear puts organization_id +
    # team_ids. Not encrypted — non-secret discovery metadata.
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookRegistration:
    """Result of registering a webhook on the provider side."""

    # IDs returned by the provider for the webhook(s) created. GitHub
    # returns one per repo, so this is a list. Used on revoke to clean up.
    provider_webhook_ids: list[str]
    # The HMAC secret we generated and gave the provider. Caller persists
    # via `store_token(webhook_secret=...)`.
    secret: str


class ProviderError(Exception):
    """Provider-side failure surfaced to the service layer."""


class OAuthCallbackError(ProviderError):
    """Callback arrived with missing or invalid parameters."""


class TokenRefreshError(ProviderError):
    """Refresh attempt failed — caller should revoke + notify the org admin."""


class WebhookRegistrationError(ProviderError):
    """Provider rejected webhook creation."""


class ProviderAdapter(ABC):
    """One concrete instance per provider. Stateless — all state lives in
    the DB / Redis / external system."""

    #: Lower-case provider id, e.g. "github". Matches `integration_oauth_tokens.provider`.
    name: str

    @abstractmethod
    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        """Build the URL we redirect the customer's browser to."""

    @abstractmethod
    async def complete_callback(
        self, params: Mapping[str, str], *, redirect_uri: str
    ) -> ProviderConnection:
        """Handle the provider's callback. Returns a fresh ProviderConnection."""

    @abstractmethod
    async def refresh(self, connection: ProviderConnection) -> ProviderConnection:
        """Re-mint or refresh the access token. Raises `TokenRefreshError`
        if the refresh path is unrecoverable (caller revokes the integration)."""

    @abstractmethod
    async def register_webhook(
        self,
        connection: ProviderConnection,
        *,
        webhook_url: str,
        secret: str,
    ) -> WebhookRegistration:
        """Register one or more webhooks on the provider side."""

    @abstractmethod
    async def revoke(self, connection: ProviderConnection) -> None:
        """Optional clean-up on disconnect (delete webhooks, revoke token).
        Best-effort: a failed revoke shouldn't block local revocation."""

"""Provider adapter registry.

One instance per provider per process. Built lazily on first access from
either env vars (dev/test) or AWS Secrets Manager (prod, when wired in C5+).

Tests override entries via `override_for_test` — bypasses the secret
fetch and lets the test inject a mock adapter directly.
"""

from __future__ import annotations

import os

from integration.app.providers.base import ProviderAdapter
from integration.app.providers.github import GitHubAppAdapter
from integration.app.providers.jira import JiraAdapter
from integration.app.providers.linear import LinearAdapter
from viberoi_shared.errors import NotFound
from viberoi_shared.logging import get_logger

logger = get_logger(__name__)

# Lazy-initialised, mutable for tests. Keys are lowercase provider names.
_REGISTRY: dict[str, ProviderAdapter] = {}


# Placeholder PEM used in dev/test if no real GitHub App private key is
# configured — the adapter is still constructed (no runtime check), so unit
# tests against mocked providers don't blow up at import time. Any actual
# call to GitHubAppAdapter._sign_app_jwt() with this key will raise inside
# PyJWT; that's the correct loud-fail behaviour.
_DEV_STUB_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nstub\n-----END PRIVATE KEY-----\n"


def _build() -> dict[str, ProviderAdapter]:
    """Build the registry from env vars. Prod wires Secrets Manager in C5+."""
    return {
        "github": GitHubAppAdapter(
            app_id=os.environ.get("VIBEROI_GITHUB_APP_ID", "stub-app-id"),
            app_slug=os.environ.get("VIBEROI_GITHUB_APP_SLUG", "viberoi-stub"),
            private_key_pem=os.environ.get(
                "VIBEROI_GITHUB_APP_PRIVATE_KEY_PEM", _DEV_STUB_PRIVATE_KEY
            ),
        ),
        "jira": JiraAdapter(
            client_id=os.environ.get("VIBEROI_JIRA_CLIENT_ID", "stub-jira-cid"),
            client_secret=os.environ.get(
                "VIBEROI_JIRA_CLIENT_SECRET", "stub-jira-csec"
            ),
        ),
        "linear": LinearAdapter(
            client_id=os.environ.get("VIBEROI_LINEAR_CLIENT_ID", "stub-lin-cid"),
            client_secret=os.environ.get(
                "VIBEROI_LINEAR_CLIENT_SECRET", "stub-lin-csec"
            ),
        ),
    }


async def get(name: str) -> ProviderAdapter:
    """Return the adapter for a provider. Raises `NotFound` for unknown names."""
    if not _REGISTRY:
        _REGISTRY.update(_build())
    adapter = _REGISTRY.get(name.lower())
    if adapter is None:
        raise NotFound(f"Unknown provider: {name}")
    return adapter


def override_for_test(name: str, adapter: ProviderAdapter) -> None:
    """Test helper — replace (or add) an adapter in the registry."""
    _REGISTRY[name.lower()] = adapter


def reset() -> None:
    """Test helper — clear the registry so the next `get` rebuilds it."""
    _REGISTRY.clear()

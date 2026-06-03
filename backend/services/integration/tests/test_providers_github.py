"""GitHub App provider tests — uses respx + a generated RSA key."""

from __future__ import annotations

import time

import httpx
import jwt
import orjson
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from integration.app import http_client
from integration.app.providers.base import (
    OAuthCallbackError,
    ProviderConnection,
    TokenRefreshError,
    WebhookRegistrationError,
)
from integration.app.providers.github import GitHubAppAdapter

_APP_ID = "lv1_test_appid"
_APP_SLUG = "viberoi-test"


@pytest.fixture
def keypair() -> tuple[str, str]:
    """Generate an RSA key for App JWT signing in tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        key.public_key()
        .public_bytes(encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo)
        .decode("utf-8")
    )
    return (private_pem, public_pem)


@pytest.fixture
def adapter(keypair: tuple[str, str]) -> GitHubAppAdapter:
    private_pem, _ = keypair
    return GitHubAppAdapter(
        app_id=_APP_ID, app_slug=_APP_SLUG, private_key_pem=private_pem
    )


@pytest.fixture(autouse=True)
async def _reset_http_client() -> None:
    await http_client.aclose()
    yield
    await http_client.aclose()


# ── authorize_url ───────────────────────────────────────────────────────────


def test_authorize_url_contains_slug_and_state(adapter: GitHubAppAdapter) -> None:
    url = adapter.authorize_url(state="abc", redirect_uri="ignored")
    assert url == "https://github.com/apps/viberoi-test/installations/new?state=abc"


# ── App JWT signing ─────────────────────────────────────────────────────────


def test_signed_app_jwt_has_correct_claims(
    adapter: GitHubAppAdapter, keypair: tuple[str, str]
) -> None:
    _, public_pem = keypair
    token = adapter._sign_app_jwt()
    decoded = jwt.decode(token, public_pem, algorithms=["RS256"])
    assert decoded["iss"] == _APP_ID
    now = int(time.time())
    assert decoded["iat"] <= now
    assert decoded["iat"] >= now - 65  # backdated by ~60s
    # exp <= 10 minutes per GitHub
    assert decoded["exp"] - decoded["iat"] <= 600


# ── complete_callback ───────────────────────────────────────────────────────


@pytest.mark.respx(base_url="https://api.github.com")
async def test_complete_callback_mints_installation_token(
    adapter: GitHubAppAdapter,
    respx_mock: respx.MockRouter,
) -> None:
    route = respx_mock.post(
        "/app/installations/12345/access_tokens"
    ).respond(
        201,
        json={
            "token": "ghs_NEWFORMAT_INSTALL_TOKEN",
            "expires_at": "2026-06-03T13:00:00Z",
            "permissions": {"contents": "read", "pull_requests": "read"},
            "repository_selection": "all",
        },
    )

    connection = await adapter.complete_callback(
        {"installation_id": "12345", "state": "ignored"},
        redirect_uri="https://app.viberoi.io/oauth/callback",
    )
    assert connection.access_token == "ghs_NEWFORMAT_INSTALL_TOKEN"
    assert connection.installation_id == "12345"
    assert connection.refresh_token is None
    assert connection.expires_at is not None
    assert connection.extra["repository_selection"] == "all"

    # Verify the request was authenticated with our App JWT
    sent_auth = route.calls.last.request.headers.get("Authorization", "")
    assert sent_auth.startswith("Bearer ")
    assert "X-GitHub-Api-Version" in route.calls.last.request.headers


@pytest.mark.respx(base_url="https://api.github.com")
async def test_complete_callback_missing_installation_id_raises(
    adapter: GitHubAppAdapter,
    respx_mock: respx.MockRouter,
) -> None:
    with pytest.raises(OAuthCallbackError):
        await adapter.complete_callback({}, redirect_uri="x")


@pytest.mark.respx(base_url="https://api.github.com")
async def test_complete_callback_github_500_raises(
    adapter: GitHubAppAdapter,
    respx_mock: respx.MockRouter,
) -> None:
    # All 3 retries fail
    respx_mock.post("/app/installations/99/access_tokens").mock(
        side_effect=[httpx.Response(500), httpx.Response(500), httpx.Response(500)]
    )
    with pytest.raises(TokenRefreshError):
        await adapter.complete_callback({"installation_id": "99"}, redirect_uri="x")


# ── refresh ────────────────────────────────────────────────────────────────


@pytest.mark.respx(base_url="https://api.github.com")
async def test_refresh_re_mints_installation_token(
    adapter: GitHubAppAdapter,
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.post("/app/installations/12345/access_tokens").respond(
        201,
        json={"token": "ghs_NEW", "expires_at": "2026-06-03T13:30:00Z"},
    )
    existing = ProviderConnection(
        access_token="ghs_OLD",
        installation_id="12345",
    )
    new_conn = await adapter.refresh(existing)
    assert new_conn.access_token == "ghs_NEW"
    assert new_conn.installation_id == "12345"


async def test_refresh_without_installation_id_raises(
    adapter: GitHubAppAdapter,
) -> None:
    existing = ProviderConnection(access_token="ghs_OLD", installation_id=None)
    with pytest.raises(TokenRefreshError):
        await adapter.refresh(existing)


# ── webhook registration ──────────────────────────────────────────────────


@pytest.mark.respx(base_url="https://api.github.com")
async def test_register_webhook_per_repo(
    adapter: GitHubAppAdapter,
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("/installation/repositories").respond(
        200,
        json={
            "repositories": [
                {"owner": {"login": "acme"}, "name": "frontend"},
                {"owner": {"login": "acme"}, "name": "backend"},
            ],
        },
    )
    respx_mock.post("/repos/acme/frontend/hooks").respond(201, json={"id": 101})
    respx_mock.post("/repos/acme/backend/hooks").respond(201, json={"id": 102})

    connection = ProviderConnection(access_token="ghs_T", installation_id="1")
    result = await adapter.register_webhook(
        connection,
        webhook_url="https://hooks.viberoi.io/webhooks/github/some-uuid",
        secret="random-secret",
    )
    assert sorted(result.provider_webhook_ids) == [
        "acme/backend:102",
        "acme/frontend:101",
    ]
    assert result.secret == "random-secret"


@pytest.mark.respx(base_url="https://api.github.com")
async def test_register_webhook_all_repos_fail_raises(
    adapter: GitHubAppAdapter,
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("/installation/repositories").respond(
        200, json={"repositories": [{"owner": {"login": "acme"}, "name": "x"}]}
    )
    respx_mock.post("/repos/acme/x/hooks").respond(403, json={"message": "forbidden"})

    with pytest.raises(WebhookRegistrationError):
        await adapter.register_webhook(
            ProviderConnection(access_token="t", installation_id="1"),
            webhook_url="u",
            secret="s",
        )


@pytest.mark.respx(base_url="https://api.github.com")
async def test_register_webhook_body_includes_expected_events(
    adapter: GitHubAppAdapter,
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("/installation/repositories").respond(
        200, json={"repositories": [{"owner": {"login": "a"}, "name": "b"}]}
    )
    route = respx_mock.post("/repos/a/b/hooks").respond(201, json={"id": 1})
    await adapter.register_webhook(
        ProviderConnection(access_token="t", installation_id="1"),
        webhook_url="https://hooks.viberoi.io/x",
        secret="sss",
    )
    body = orjson.loads(route.calls.last.request.content)
    assert body["name"] == "web"
    assert body["active"] is True
    assert "push" in body["events"]
    assert "pull_request" in body["events"]
    assert body["config"]["url"] == "https://hooks.viberoi.io/x"
    assert body["config"]["secret"] == "sss"
    assert body["config"]["content_type"] == "json"

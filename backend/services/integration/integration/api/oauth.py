"""OAuth-flow endpoints.

  POST /integrations/{provider}/connect   — OrgAdmin starts a connection
  GET  /integrations/{provider}/callback  — provider redirects here

The callback is NOT Cognito-authenticated. The OAuth `state` parameter
ties the callback back to the (org_id, developer_id) that initiated.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from integration.app.auth import IntegrationAuthContext, require_role
from integration.app.orchestrator import complete_connect, initiate_connect
from integration.app.providers.base import OAuthCallbackError
from integration.schema.responses import ConnectResponse
from viberoi_shared.errors import NotFound
from viberoi_shared.integrations.oauth_state import OAuthStateError
from viberoi_shared.logging import get_logger
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()

# Defaults for V1 — these become env-driven via SharedSettings in C5
# (callback redirect_uri is registered with the provider at App-creation
# time so it has to match between here and the App config).
ALLOWED_PROVIDERS = {"github", "jira", "linear"}
WEBHOOK_BASE_URL = "https://hooks.viberoi.io"
CALLBACK_BASE_URL = "https://api.viberoi.io/integrations"
FRONTEND_ERROR_BASE = "https://app.viberoi.io/settings/integrations"


def _callback_uri(provider: str) -> str:
    return f"{CALLBACK_BASE_URL}/{provider}/callback"


def _redirect_to_frontend(query: str) -> Response:
    return RedirectResponse(
        url=f"{FRONTEND_ERROR_BASE}?{query}", status_code=302
    )


@router.post(
    "/{provider}/connect",
    response_model=ConnectResponse,
)
async def post_connect(
    provider: str,
    ctx: Annotated[
        IntegrationAuthContext, Depends(require_role(Role.ORG_ADMIN))
    ],
) -> ConnectResponse:
    """Return the URL to redirect the customer's browser to."""
    if provider not in ALLOWED_PROVIDERS:
        raise NotFound(f"Unknown provider: {provider}")

    result = await initiate_connect(
        org_id=ctx.org_id,
        developer_id=ctx.developer_id,
        provider=provider,
        redirect_uri=_callback_uri(provider),
    )
    return ConnectResponse(authorize_url=result.authorize_url)


@router.get("/{provider}/callback")
async def get_callback(provider: str, request: Request) -> Response:
    """OAuth callback — state-authenticated; no Cognito JWT.

    On success: 302 to frontend with `status=ok&id=...`.
    On failure: 302 to frontend with `err=<reason>` — never expose
    exception details, never return a JSON body.
    """
    if provider not in ALLOWED_PROVIDERS:
        return _redirect_to_frontend("err=unknown_provider")

    callback_params = dict(request.query_params)

    try:
        result = await complete_connect(
            provider=provider,
            callback_params=callback_params,
            redirect_uri=_callback_uri(provider),
            webhook_base_url=WEBHOOK_BASE_URL,
        )
    except OAuthStateError:
        logger.warning("oauth_callback_bad_state", provider=provider)
        return _redirect_to_frontend("err=oauth_state")
    except OAuthCallbackError:
        logger.warning("oauth_callback_provider_rejected", provider=provider)
        return _redirect_to_frontend("err=user_cancelled")
    except Exception as e:  # noqa: BLE001
        # Don't leak details — generic error redirect.
        logger.exception(
            "oauth_callback_unhandled", provider=provider, error=str(e)
        )
        return _redirect_to_frontend("err=internal")

    return _redirect_to_frontend(
        f"status={result.webhook_registration_status}&id={result.integration_id}"
    )

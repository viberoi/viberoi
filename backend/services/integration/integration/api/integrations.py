"""Integration list + disconnect routes.

  GET    /integrations              — list connected providers (any role)
  DELETE /integrations/{provider}   — disconnect (OrgAdmin only)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from integration.app.auth import IntegrationAuthContext, require_role
from integration.app.orchestrator import disconnect, list_integrations
from integration.schema.responses import IntegrationSummary
from viberoi_shared.logging import get_logger
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=list[IntegrationSummary])
async def list_integrations_route(
    ctx: Annotated[
        IntegrationAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD, Role.DEVELOPER)),
    ],
) -> list[IntegrationSummary]:
    rows = await list_integrations(org_id=ctx.org_id)
    return [IntegrationSummary(**row) for row in rows]


@router.delete("/{provider}", status_code=http_status.HTTP_204_NO_CONTENT)
async def disconnect_route(
    provider: str,
    ctx: Annotated[
        IntegrationAuthContext, Depends(require_role(Role.ORG_ADMIN))
    ],
) -> None:
    await disconnect(org_id=ctx.org_id, provider=provider)

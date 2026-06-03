"""Integration list + disconnect + sync routes.

  GET    /integrations               — list connected providers (any role)
  DELETE /integrations/{provider}    — disconnect (OrgAdmin only)
  POST   /integrations/{provider}/sync — enqueue a manual delta sync
                                          (OrgAdmin or TeamLead)
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from integration.app.auth import IntegrationAuthContext, require_role
from integration.app.orchestrator import disconnect, list_integrations
from integration.app.providers import registry
from integration.schema.responses import IntegrationSummary, SyncEnqueuedResponse
from viberoi_shared.logging import get_logger
from viberoi_shared.sqs import publish as sqs_publish
from viberoi_shared.types.enums import Role

logger = get_logger(__name__)

router = APIRouter()

BACKFILL_QUEUE = "backfill_jobs"


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


@router.post("/{provider}/sync", response_model=SyncEnqueuedResponse)
async def sync_route(
    provider: str,
    ctx: Annotated[
        IntegrationAuthContext,
        Depends(require_role(Role.ORG_ADMIN, Role.TEAM_LEAD)),
    ],
) -> SyncEnqueuedResponse:
    """Enqueue a manual delta sync. The consumer picks it up + dispatches."""
    if provider not in registry.SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="unknown_provider",
        )
    trace_id = uuid4()
    await sqs_publish(
        BACKFILL_QUEUE,
        {
            "org_id": str(ctx.org_id),
            "provider": provider,
            "sync_type": "manual",
            "requested_by": str(ctx.developer_id),
            "trace_id": str(trace_id),
        },
    )
    logger.info(
        "sync_enqueued",
        provider=provider,
        org_id=str(ctx.org_id),
        developer_id=str(ctx.developer_id),
        trace_id=str(trace_id),
    )
    return SyncEnqueuedResponse(sync_type="manual", trace_id=trace_id)

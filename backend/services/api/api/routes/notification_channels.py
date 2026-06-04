"""Notification channel config — read + upsert + disable.

OrgAdmin-only. The webhook URL is KMS-encrypted via the shared
notifications repository; it is NEVER returned in any GET response —
only an `has_webhook_url` boolean indicates configuration state.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict

from api.app.auth import ApiAuthContext, require_role
from api.schema.responses import (
    NotificationChannelListResponse,
    NotificationChannelSummary,
)
from viberoi_shared.db import org_scoped_session
from viberoi_shared.errors import NotFound, ValidationFailed
from viberoi_shared.logging import get_logger
from viberoi_shared.notifications import (
    NotificationChannel,
    assert_safe_slack_webhook_url,
    disable_channel,
    upsert_channel,
)
from viberoi_shared.types.enums import Role
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter()

SUPPORTED_CHANNELS = ("slack",)


class UpsertChannelRequest(BaseModel):
    """`POST /notifications/channels` body — only Slack today."""

    model_config = ConfigDict(extra="forbid")

    channel: Literal["slack"]
    webhook_url: str


@router.get("", response_model=NotificationChannelListResponse)
async def list_route(
    ctx: Annotated[
        ApiAuthContext, Depends(require_role(Role.ORG_ADMIN))
    ],
) -> NotificationChannelListResponse:
    """List the org's channels. Decrypted webhook URL is NOT returned —
    `has_webhook_url` boolean only."""
    async with org_scoped_session(ctx.org_id) as db:
        stmt = (
            select(NotificationChannel)
            .where(NotificationChannel.org_id == ctx.org_id)
            .order_by(NotificationChannel.channel)
        )
        rows = list((await db.execute(stmt)).scalars().all())
    return NotificationChannelListResponse(
        items=[
            NotificationChannelSummary(
                id=row.id,
                channel=row.channel,
                has_webhook_url=row.webhook_url_ciphertext is not None,
                enabled=row.enabled,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    )


@router.post(
    "",
    response_model=NotificationChannelSummary,
    status_code=http_status.HTTP_201_CREATED,
)
async def upsert_route(
    body: UpsertChannelRequest,
    ctx: Annotated[
        ApiAuthContext, Depends(require_role(Role.ORG_ADMIN))
    ],
) -> NotificationChannelSummary:
    """Upsert a channel. The SSRF guard fires here too — defence in
    depth alongside the shared repository's check."""
    if body.channel == "slack":
        try:
            assert_safe_slack_webhook_url(body.webhook_url)
        except ValueError as e:
            raise ValidationFailed(str(e)) from e

    async with org_scoped_session(ctx.org_id) as db:
        channel_id = await upsert_channel(
            db,
            org_id=ctx.org_id,
            channel=body.channel,
            webhook_url=body.webhook_url,
            enabled=True,
        )
        # Round-trip to fetch the persisted row for accurate timestamps.
        row = (
            await db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.id == channel_id
                )
            )
        ).scalar_one()
    logger.info(
        "notification_channel_upserted",
        org_id=str(ctx.org_id),
        channel=body.channel,
    )
    return NotificationChannelSummary(
        id=row.id,
        channel=row.channel,
        has_webhook_url=row.webhook_url_ciphertext is not None,
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete(
    "/{channel}",
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def disable_route(
    channel: str,
    ctx: Annotated[
        ApiAuthContext, Depends(require_role(Role.ORG_ADMIN))
    ],
) -> None:
    """Soft-disable a channel. Re-upserting with `enabled=true` reactivates."""
    if channel not in SUPPORTED_CHANNELS:
        raise NotFound(f"Unknown channel: {channel}")
    async with org_scoped_session(ctx.org_id) as db:
        ok = await disable_channel(db, org_id=ctx.org_id, channel=channel)
    if not ok:
        raise NotFound(f"No {channel} channel configured for this org.")
    logger.info(
        "notification_channel_disabled",
        org_id=str(ctx.org_id),
        channel=channel,
    )

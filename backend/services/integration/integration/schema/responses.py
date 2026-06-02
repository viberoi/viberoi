"""Pydantic response models for the Integration service."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class IntegrationSummary(BaseModel):
    """One row in the `GET /integrations` response."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    provider: str
    installed_by_developer_id: UUID | None
    expires_at: datetime | None
    scope: str | None
    created_at: datetime
    webhook_registration_status: str | None
    last_sync_at: datetime | None
    revoked: bool


class ConnectResponse(BaseModel):
    """`POST /integrations/{provider}/connect` returns the URL to redirect to."""

    model_config = ConfigDict(extra="forbid")

    authorize_url: str


class SyncEnqueuedResponse(BaseModel):
    """`POST /integrations/{provider}/sync` ack."""

    model_config = ConfigDict(extra="forbid")

    sync_type: str
    enqueued: bool = True
    trace_id: UUID

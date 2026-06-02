"""Pydantic request models for the Ingest service."""

from pydantic import BaseModel, ConfigDict

from viberoi_shared.types import Session


class IngestRequest(BaseModel):
    """Single-session push from the agent.

    The agent gzips this whole payload and HMAC-signs it before POST.
    The service decompresses, verifies HMAC, then validates against
    this schema.
    """

    model_config = ConfigDict(extra="forbid")

    session: Session

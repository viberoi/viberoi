"""Pydantic response models for the Ingest service."""

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class IngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: int
    rejected: int
    message: str | None = None

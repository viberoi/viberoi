"""Liveness and readiness probes."""

from fastapi import APIRouter

from ingest.schema.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness — fast, no dependencies. 200 if the process is alive."""
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
async def readyz() -> HealthResponse:
    """Readiness — will check Postgres + S3 when wiring lands. Slice 1 stub."""
    return HealthResponse(status="ok")

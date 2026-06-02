"""Liveness and readiness probes."""

from fastapi import APIRouter
from sqlalchemy import text

from ingest.schema.responses import HealthResponse
from viberoi_shared.aws import s3_client
from viberoi_shared.db import superuser_session
from viberoi_shared.errors import ExternalServiceError
from viberoi_shared.logging import get_logger
from viberoi_shared.s3 import RAW_BUCKET

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness — fast, no dependencies. 200 if the process is alive."""
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
async def readyz() -> HealthResponse:
    """Readiness — verify Postgres + S3 reachable before accepting traffic.

    Returns 503 (via `ExternalServiceError`) if any dependency is down,
    so the load balancer / orchestrator pulls this instance out of rotation.
    """
    try:
        async with superuser_session() as db:
            await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("readyz_postgres_unreachable", error=str(e))
        raise ExternalServiceError("Postgres unreachable") from e

    try:
        async with s3_client() as s3:
            await s3.head_bucket(Bucket=RAW_BUCKET)
    except Exception as e:
        logger.warning("readyz_s3_unreachable", error=str(e))
        raise ExternalServiceError("S3 unreachable") from e

    return HealthResponse(status="ok")

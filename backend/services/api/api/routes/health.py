"""Liveness and readiness probes."""

from fastapi import APIRouter
from sqlalchemy import text

from api.schema.responses import HealthResponse
from viberoi_shared.db import superuser_session
from viberoi_shared.errors import ExternalServiceError
from viberoi_shared.logging import get_logger
from viberoi_shared.redis import get_client

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness — fast, no dependencies."""
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
async def readyz() -> HealthResponse:
    """Readiness — verify Postgres + Redis reachable before accepting traffic."""
    try:
        async with superuser_session() as db:
            await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("readyz_postgres_unreachable", error_type=type(e).__name__)
        raise ExternalServiceError("Postgres unreachable") from e

    try:
        await get_client().ping()
    except Exception as e:
        logger.warning("readyz_redis_unreachable", error_type=type(e).__name__)
        raise ExternalServiceError("Redis unreachable") from e

    return HealthResponse(status="ok")

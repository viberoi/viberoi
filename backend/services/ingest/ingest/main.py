"""Ingest service FastAPI app entry."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ingest.api import health, sessions
from viberoi_shared.errors.handlers import register_handlers
from viberoi_shared.logging import RequestIdMiddleware, configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("ingest_startup")
    yield
    logger.info("ingest_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="VibeROI Ingest",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(RequestIdMiddleware)
    register_handlers(app)
    app.include_router(health.router)
    app.include_router(sessions.router, prefix="/ingest", tags=["ingest"])
    return app


app = create_app()

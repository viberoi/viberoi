"""API service FastAPI app entry."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import (
    developers,
    health,
    invitations,
    kpis,
    me,
    notification_channels,
    sessions,
    sprints,
    tickets,
)
from viberoi_shared.errors.handlers import register_handlers
from viberoi_shared.logging import RequestIdMiddleware, configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("api_startup")
    yield
    logger.info("api_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="VibeROI API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(RequestIdMiddleware)
    register_handlers(app)
    app.include_router(health.router)
    app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
    app.include_router(sprints.router, prefix="/sprints", tags=["sprints"])
    app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
    app.include_router(kpis.router, prefix="/kpis", tags=["kpis"])
    app.include_router(
        developers.router, prefix="/developers", tags=["developers"]
    )
    app.include_router(
        notification_channels.router,
        prefix="/notifications/channels",
        tags=["notifications"],
    )
    app.include_router(
        invitations.router, prefix="/invitations", tags=["invitations"]
    )
    app.include_router(me.router, prefix="/me", tags=["me"])
    return app


app = create_app()

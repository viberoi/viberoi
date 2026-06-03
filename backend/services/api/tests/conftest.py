"""Shared pytest fixtures for the API service tests."""

from uuid import uuid4

import pytest
from api.app.auth import ApiAuthContext, authenticate
from api.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient

from viberoi_shared.types.enums import Role


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def org_admin_ctx() -> ApiAuthContext:
    return ApiAuthContext(
        developer_id=uuid4(), org_id=uuid4(), role=Role.ORG_ADMIN, team_id=None
    )


@pytest.fixture
def team_lead_ctx() -> ApiAuthContext:
    return ApiAuthContext(
        developer_id=uuid4(), org_id=uuid4(), role=Role.TEAM_LEAD, team_id=uuid4()
    )


@pytest.fixture
def developer_ctx() -> ApiAuthContext:
    return ApiAuthContext(
        developer_id=uuid4(), org_id=uuid4(), role=Role.DEVELOPER, team_id=uuid4()
    )


@pytest.fixture
def client_as(app: FastAPI):
    """Return a callable: `client_as(ctx)` → TestClient with auth overridden."""

    def _build(ctx: ApiAuthContext) -> TestClient:
        app.dependency_overrides[authenticate] = lambda: ctx
        return TestClient(app, raise_server_exceptions=False)

    yield _build
    app.dependency_overrides.clear()

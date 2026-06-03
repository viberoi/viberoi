"""Shared pytest fixtures for the Integration service tests."""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from integration.app.auth import IntegrationAuthContext, authenticate
from integration.main import create_app

from viberoi_shared.types.enums import Role


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def org_admin_ctx() -> IntegrationAuthContext:
    return IntegrationAuthContext(
        developer_id=uuid4(), org_id=uuid4(), role=Role.ORG_ADMIN, team_id=None
    )


@pytest.fixture
def team_lead_ctx() -> IntegrationAuthContext:
    return IntegrationAuthContext(
        developer_id=uuid4(), org_id=uuid4(), role=Role.TEAM_LEAD, team_id=uuid4()
    )


@pytest.fixture
def developer_ctx() -> IntegrationAuthContext:
    return IntegrationAuthContext(
        developer_id=uuid4(), org_id=uuid4(), role=Role.DEVELOPER, team_id=uuid4()
    )


@pytest.fixture
def client_as(app: FastAPI):
    """Return a callable: `client_as(ctx)` → TestClient with auth overridden."""

    def _build(ctx: IntegrationAuthContext) -> TestClient:
        app.dependency_overrides[authenticate] = lambda: ctx
        return TestClient(app, raise_server_exceptions=False)

    yield _build
    app.dependency_overrides.clear()

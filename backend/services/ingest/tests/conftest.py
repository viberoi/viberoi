"""Shared pytest fixtures for ingest service tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ingest.main import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)

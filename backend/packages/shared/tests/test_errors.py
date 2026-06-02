"""Error envelope handler produces the standard shape."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from viberoi_shared.errors import Forbidden, NotFound, Unauthorized, VibeRoiError
from viberoi_shared.errors.handlers import register_handlers


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    register_handlers(app)

    @app.get("/unauthorized")
    async def _u() -> None:
        raise Unauthorized

    @app.get("/forbidden")
    async def _f() -> None:
        raise Forbidden

    @app.get("/not_found")
    async def _nf() -> None:
        raise NotFound

    @app.get("/custom_details")
    async def _cd() -> None:
        raise VibeRoiError("Custom message", details={"why": "tests"})

    @app.get("/unhandled")
    async def _crash() -> None:
        raise RuntimeError("boom")

    return app


def test_unauthorized_envelope(app: FastAPI) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/unauthorized")
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "Authentication required."


def test_forbidden_envelope(app: FastAPI) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/forbidden")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_not_found_envelope(app: FastAPI) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/not_found")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_details_included(app: FastAPI) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/custom_details")
    body = r.json()
    assert body["error"]["details"] == {"why": "tests"}


def test_unhandled_is_safe(app: FastAPI) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/unhandled")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "internal_error"
    # The original exception message must NOT leak to the client
    assert "boom" not in body["error"]["message"]

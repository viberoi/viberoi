"""HTTP client tests — uses respx to mock httpx without real network."""

from __future__ import annotations

import httpx
import pytest
import respx

from integration.app import http_client


@pytest.fixture(autouse=True)
async def _reset_client() -> None:
    """Reset the singleton so each test gets a fresh client (and so
    respx's transport patching applies)."""
    await http_client.aclose()
    yield
    await http_client.aclose()


@pytest.mark.respx(base_url="https://api.example.com")
async def test_2xx_response_returned_immediately(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("/ok").respond(200, json={"hello": "world"})
    response = await http_client.request("GET", "https://api.example.com/ok")
    assert response.status_code == 200
    assert response.json() == {"hello": "world"}


@pytest.mark.respx(base_url="https://api.example.com")
async def test_4xx_response_returned_without_retry(
    respx_mock: respx.MockRouter,
) -> None:
    route = respx_mock.get("/forbidden").respond(403)
    response = await http_client.request("GET", "https://api.example.com/forbidden")
    assert response.status_code == 403
    assert route.call_count == 1


@pytest.mark.respx(base_url="https://api.example.com")
async def test_5xx_response_triggers_retries(
    respx_mock: respx.MockRouter,
) -> None:
    route = respx_mock.get("/flaky").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json={"recovered": True}),
        ]
    )
    response = await http_client.request("GET", "https://api.example.com/flaky")
    assert response.status_code == 200
    assert route.call_count == 3


@pytest.mark.respx(base_url="https://api.example.com")
async def test_5xx_exhaust_retries_returns_last_response(
    respx_mock: respx.MockRouter,
) -> None:
    route = respx_mock.get("/always-down").mock(
        side_effect=[httpx.Response(500), httpx.Response(500), httpx.Response(500)]
    )
    response = await http_client.request("GET", "https://api.example.com/always-down")
    assert response.status_code == 500
    assert route.call_count == 3


@pytest.mark.respx(base_url="https://api.example.com")
async def test_network_error_triggers_retries(
    respx_mock: respx.MockRouter,
) -> None:
    route = respx_mock.get("/timeout").mock(
        side_effect=[
            httpx.ConnectError("connection refused"),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    response = await http_client.request("GET", "https://api.example.com/timeout")
    assert response.status_code == 200
    assert route.call_count == 2


@pytest.mark.respx(base_url="https://api.example.com")
async def test_network_error_exhausted_raises(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("/no-network").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    with pytest.raises(httpx.ConnectError):
        await http_client.request("GET", "https://api.example.com/no-network")


async def test_get_client_returns_singleton() -> None:
    c1 = http_client.get_http_client()
    c2 = http_client.get_http_client()
    assert c1 is c2


@pytest.mark.respx(base_url="https://api.example.com")
async def test_user_agent_header_sent(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/").respond(200)
    await http_client.request("GET", "https://api.example.com/")
    assert "User-Agent" in route.calls.last.request.headers
    assert route.calls.last.request.headers["User-Agent"].startswith("VibeROI-Integration")

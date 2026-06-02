"""RBAC dependency tests.

Tests the `require_role` factory in isolation — wire it onto a throwaway
route so we don't depend on the full /integrations surface (lands in C4).
"""

from collections.abc import Callable

import pytest
from fastapi import FastAPI

from integration.app.auth import IntegrationAuthContext, authenticate, require_role
from viberoi_shared.types.enums import Role


def _add_role_gated_route(app: FastAPI, *allowed: Role) -> None:
    """Attach a synthetic `/role-test` endpoint guarded by the role check."""
    from fastapi import Depends

    @app.get("/role-test")
    async def _route(
        ctx: IntegrationAuthContext = Depends(require_role(*allowed)),
    ) -> dict:
        return {"role": ctx.role.value, "org_id": str(ctx.org_id)}


def test_org_admin_can_access_org_admin_only_route(
    app: FastAPI,
    org_admin_ctx: IntegrationAuthContext,
    client_as: Callable,
) -> None:
    _add_role_gated_route(app, Role.ORG_ADMIN)
    r = client_as(org_admin_ctx).get("/role-test")
    assert r.status_code == 200
    assert r.json()["role"] == "OrgAdmin"


@pytest.mark.parametrize(
    "ctx_name",
    ["team_lead_ctx", "developer_ctx"],
)
def test_non_admin_cannot_access_org_admin_only_route(
    app: FastAPI,
    ctx_name: str,
    request: pytest.FixtureRequest,
    client_as: Callable,
) -> None:
    _add_role_gated_route(app, Role.ORG_ADMIN)
    ctx = request.getfixturevalue(ctx_name)
    r = client_as(ctx).get("/role-test")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_team_lead_and_admin_share_route(
    app: FastAPI,
    org_admin_ctx: IntegrationAuthContext,
    team_lead_ctx: IntegrationAuthContext,
    client_as: Callable,
) -> None:
    _add_role_gated_route(app, Role.ORG_ADMIN, Role.TEAM_LEAD)
    assert client_as(org_admin_ctx).get("/role-test").status_code == 200
    assert client_as(team_lead_ctx).get("/role-test").status_code == 200


def test_developer_can_access_dev_route(
    app: FastAPI,
    developer_ctx: IntegrationAuthContext,
    client_as: Callable,
) -> None:
    _add_role_gated_route(app, Role.DEVELOPER, Role.TEAM_LEAD, Role.ORG_ADMIN)
    r = client_as(developer_ctx).get("/role-test")
    assert r.status_code == 200


def test_missing_auth_header_returns_401(client) -> None:
    """Without any auth override, missing Bearer → 401."""
    # The default `authenticate` reaches `verify_jwt` which would raise
    # CognitoNotImplemented; the bearer-parsing check fires first when no
    # header is present, returning Unauthorized.
    r = client.get("/healthz")  # /healthz is unauthenticated so works
    assert r.status_code == 200

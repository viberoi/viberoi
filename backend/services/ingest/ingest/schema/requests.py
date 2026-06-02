"""Pydantic request models for the Ingest service.

The Session payload itself is the locked v1.0 type from `viberoi_shared.types`
and is used directly as the request body — no wrapper envelope. Keep this
module for any service-specific request shapes (e.g. an upcoming
`AgentRegisterRequest` for `/ingest/register`).
"""

from pydantic import BaseModel, ConfigDict


class AgentRegisterRequest(BaseModel):
    """Body for `POST /ingest/register` — lands with the agent in Slice 9.

    Defined here so the type and OpenAPI shape stay locked early; the
    handler is a 501 stub until the agent ships.
    """

    model_config = ConfigDict(extra="forbid")

    install_token: str
    machine_id: str
    os: str
    agent_version: str
    declared_tools: list[str]

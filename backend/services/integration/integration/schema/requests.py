"""Pydantic request models for the Integration service.

Most provider-specific request bodies land alongside the routes in C4.
This module currently holds shared/admin-facing request shapes.
"""

from pydantic import BaseModel, ConfigDict


class ConnectRequest(BaseModel):
    """`POST /integrations/{provider}/connect` body — currently empty.

    The provider goes in the path; org and developer come from the Cognito JWT.
    A future field may carry an opt-in flag for repo-scope preselection.
    """

    model_config = ConfigDict(extra="forbid")


class SyncRequest(BaseModel):
    """`POST /integrations/{provider}/sync` body."""

    model_config = ConfigDict(extra="forbid")

    sync_type: str = "delta_5m"  # one of: initial_90d | delta_5m | full | manual

"""Pydantic models shared across services.

The session object (locked schema v1.0), KPI structs, RBAC enums,
SQS message envelopes, Cognito claims. The Python source of truth;
the Go agent mirrors `Session` in `agent/pkg/schema`.
"""

from viberoi_shared.types.enums import (
    AttributionMethod,
    CaptureMode,
    DataSource,
    HallucinationRisk,
    PricingType,
    PricingUnit,
    Role,
    SessionMode,
    Surface,
    Tool,
)
from viberoi_shared.types.session import (
    SCHEMA_VERSION,
    Activity,
    Attribution,
    CodeOutput,
    Meta,
    Pricing,
    Quality,
    Repository,
    Session,
    Timing,
    Tokens,
    ToolInfo,
)

__all__ = [
    "SCHEMA_VERSION",
    "Activity",
    "Attribution",
    "AttributionMethod",
    "CaptureMode",
    "CodeOutput",
    "DataSource",
    "HallucinationRisk",
    "Meta",
    "Pricing",
    "PricingType",
    "PricingUnit",
    "Quality",
    "Repository",
    "Role",
    "Session",
    "SessionMode",
    "Surface",
    "Timing",
    "Tokens",
    "Tool",
    "ToolInfo",
]

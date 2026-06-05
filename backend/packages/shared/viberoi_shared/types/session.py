"""Session object — locked schema v1.0.

Authoritative spec:
  `frontend/VibeROI-DataSource-Master-final.md`
  § "SESSION OBJECT SCHEMA — LOCKED"

The Go agent mirrors this struct in `agent/pkg/schema`. Changes here
require a matching change there and a `schema_version` bump. The Worker
accepts current + previous version for one release after a bump.

Design principles:
- One session object = one AI working session on one branch
- Only stores what was *observed* — computed KPIs derived at query time
- Never stores prompt text, code content, or args/results — only metadata
- Every field has a verified source from a real tool's local store or API
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt

from viberoi_shared.types.enums import (
    AttributionMethod,
    CaptureMode,
    DataSource,
    HallucinationRisk,
    PricingType,
    PricingUnit,
    SessionMode,
    Surface,
    Tool,
)

SCHEMA_VERSION = "1.0"


class Pricing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: PricingType
    unit: PricingUnit
    rate_usd: NonNegativeFloat = Field(
        description="Per-unit cost in USD; 0 for flat subscriptions.",
    )


class ToolInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Tool
    surface: Surface
    version: str
    model: str
    capture_mode: CaptureMode
    pricing_model: Pricing


class Timing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at: datetime
    ended_at: datetime
    active_duration_min: NonNegativeInt
    first_commit_at: datetime | None = None
    time_to_first_commit_min: int | None = Field(
        default=None,
        description="Minutes from session start to first commit; null if no commit.",
    )


class Tokens(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: NonNegativeInt
    output: NonNegativeInt
    cache_read: NonNegativeInt = 0
    cache_write: NonNegativeInt = 0
    total_cost_usd: NonNegativeFloat
    is_estimated: bool = Field(
        description="False = exact from local source; True = estimated or API-derived.",
    )
    reconciled: bool = False
    reconciled_at: datetime | None = None


class Activity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_count: NonNegativeInt
    mode: SessionMode
    is_agentic: bool
    subagent_count: NonNegativeInt = 0
    files_touched: list[str] = Field(
        default_factory=list,
        description="File paths touched in session. PATHS ONLY — never file contents.",
    )
    files_touched_count: NonNegativeInt = 0


class CodeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lines_added: NonNegativeInt = 0
    lines_deleted: NonNegativeInt = 0
    lines_accepted: NonNegativeInt = 0
    lines_reverted: NonNegativeInt = 0
    is_committed: bool = False
    commit_hashes: list[str] = Field(default_factory=list)
    uncommitted_at_end: bool = False


class Repository(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    origin_cwd: str = Field(description="Real repo root; never the worktree path.")
    branch: str = Field(description="Resolved real branch (not worktree).")
    raw_branch: str | None = Field(
        default=None,
        description="Branch as recorded by the tool; differs from `branch` for worktrees.",
    )
    is_worktree: bool = False


class Attribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str | None = None
    epic_id: str | None = None
    sprint_id: str | None = None
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    signals: list[str] = Field(default_factory=list)
    method: AttributionMethod = AttributionMethod.BRANCH_PARSE


class Quality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_restarts: NonNegativeInt = 0
    file_oscillations: NonNegativeInt = 0
    token_spike_detected: bool = False
    no_commit_duration_min: NonNegativeInt = 0
    is_refunded: bool = False
    hallucination_risk: HallucinationRisk = HallucinationRisk.NONE


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    captured_at: datetime
    agent_version: str
    data_sources: list[DataSource] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION


class Session(BaseModel):
    """The single source of truth for an AI working session.

    Locked at schema_version 1.0. Bump version on any breaking change;
    the Worker accepts current + previous version for one release after a bump.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str
    developer_id: str
    org_id: str
    # Stable per-machine sha256 hex from `viberoi-agent/pkg/machineid`.
    # Worker copies this to `developers.machine_id_hash` on first push
    # from a given developer; subsequent pushes from a different machine
    # signal cross-device reuse (per-active-device billing input).
    # Optional for backward compatibility with v1.0 agents that don't yet
    # emit it — defaults to empty string.
    machine_id: str = ""

    tool: ToolInfo
    timing: Timing
    tokens: Tokens
    activity: Activity
    code_output: CodeOutput
    repository: Repository
    attribution: Attribution
    quality: Quality
    meta: Meta

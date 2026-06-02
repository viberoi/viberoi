"""Enums used across the codebase.

Stored as strings in DB and JSON. Use `StrEnum` so values serialize
cleanly via Pydantic v2 without custom encoders.
"""

from enum import StrEnum


class Role(StrEnum):
    """RBAC roles. Mirrored as a Cognito group per user."""

    ORG_ADMIN = "OrgAdmin"
    TEAM_LEAD = "TeamLead"
    DEVELOPER = "Developer"


class Tool(StrEnum):
    """Supported AI coding tools."""

    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    KIRO = "kiro"
    COPILOT = "copilot"
    WINDSURF = "windsurf"
    JETBRAINS_AI = "jetbrains-ai"


class Surface(StrEnum):
    """Where the tool runs (per session)."""

    DESKTOP_APP = "desktop_app"
    CLI = "cli"
    VSCODE_EXTENSION = "vscode_extension"
    STANDALONE_IDE = "standalone_ide"


class CaptureMode(StrEnum):
    """How token data was acquired for a session."""

    LOCAL_EXACT = "local_exact"
    LOCAL_ESTIMATED = "local_estimated"
    API_ONLY = "api_only"


class PricingType(StrEnum):
    SUBSCRIPTION = "subscription"
    API_KEY = "api_key"
    CREDITS = "credits"
    SEAT = "seat"


class PricingUnit(StrEnum):
    TOKENS = "tokens"
    CREDITS = "credits"
    PREMIUM_REQUESTS = "premium_requests"


class SessionMode(StrEnum):
    AGENT = "agent"
    CHAT = "chat"
    PLAN = "plan"
    EDIT = "edit"
    ASK = "ask"


class AttributionMethod(StrEnum):
    BRANCH_PARSE = "branch_parse"
    KIRO_NATIVE = "kiro_native"
    MANUAL = "manual"
    MANUAL_CONFIRM = "manual_confirm"


class HallucinationRisk(StrEnum):
    NONE = "none"
    WATCH = "watch"
    ALERT = "alert"


class DataSource(StrEnum):
    """Source identifiers that fed a session object."""

    LOCAL_JSONL = "local_jsonl"
    LOCAL_SQLITE = "local_sqlite"
    GIT_DIFF = "git_diff"
    WORKTREE_MAP = "worktree_map"
    AWS_S3_CSV = "aws_s3_csv"
    GITHUB_API = "github_api"
    ANTHROPIC_ADMIN_API = "anthropic_admin_api"

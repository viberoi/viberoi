"""Settings loader (pydantic-settings).

Resolves env vars + `.env.local` + Secrets Manager. Per-service settings
extend `SharedSettings` with their own fields.
"""

from viberoi_shared.config.settings import Env, SharedSettings, get_settings

__all__ = ["Env", "SharedSettings", "get_settings"]

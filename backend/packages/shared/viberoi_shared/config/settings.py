"""Settings loader.

Resolves config in this order:
  1. Environment variables (prefix `VIBEROI_`)
  2. `.env.local` (dev only; gitignored)
  3. AWS Secrets Manager — lazy via `viberoi_shared.secrets.get(key)`

Per-service settings extend `SharedSettings` with their own fields.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"
    TEST = "test"


class SharedSettings(BaseSettings):
    """Base settings every service inherits from."""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        env_prefix="VIBEROI_",
        extra="ignore",
        case_sensitive=False,
    )

    env: Env = Env.DEV
    service_name: str = "unknown"
    log_level: str = "INFO"

    # AWS
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = None  # set to http://localhost:4566 for LocalStack

    # Database
    # `database_url`: regular RLS-respecting user used by services at runtime.
    # `database_admin_url`: BYPASSRLS user used ONLY by Alembic migrations and
    # `viberoi_shared.db.superuser_session()`. Sync driver (`+psycopg`) because
    # Alembic doesn't run async.
    database_url: str = "postgresql+asyncpg://viberoi:viberoi@localhost:5432/viberoi"
    database_admin_url: str = (
        "postgresql+psycopg://viberoi_admin:viberoi_admin@localhost:5432/viberoi"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout_s: int = 30

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # KMS
    kms_key_id: str = "alias/viberoi-pii"

    # Crypto (Argon2id parameters — OWASP 2024 recommendation)
    argon2_time_cost: int = 3
    argon2_memory_cost_kib: int = 65536  # 64 MB
    argon2_parallelism: int = 4

    # Tracing
    otel_endpoint: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> SharedSettings:
    """Singleton; instantiate once per process."""
    return SharedSettings()

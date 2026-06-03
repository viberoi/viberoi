"""Typed boto3 / aioboto3 client factories.

Services NEVER `import boto3` directly (ruff banned-api enforces).
They use these helpers, which:
  - apply standard retry config and timeouts
  - use IAM role credentials in prod (no env vars needed)
  - point at LocalStack in dev when `aws_endpoint_url` is set in settings

Usage:
    from viberoi_shared.aws import kms_client

    async with kms_client() as kms:
        resp = await kms.generate_data_key(KeyId=..., KeySpec="AES_256")
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.config import Config

from viberoi_shared.config import get_settings

# Standard retry + timeout config applied to all AWS clients.
_BOTO_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=30,
)


def _session() -> aioboto3.Session:
    return aioboto3.Session()


def _client_kwargs() -> dict[str, Any]:
    s = get_settings()
    kwargs: dict[str, Any] = {
        "region_name": s.aws_region,
        "config": _BOTO_CONFIG,
    }
    if s.aws_endpoint_url:
        # LocalStack — also need placeholder credentials (LocalStack accepts anything).
        kwargs["endpoint_url"] = s.aws_endpoint_url
        kwargs["aws_access_key_id"] = "test"
        kwargs["aws_secret_access_key"] = "test"  # noqa: S105
    return kwargs


@asynccontextmanager
async def kms_client() -> AsyncIterator[Any]:
    async with _session().client("kms", **_client_kwargs()) as client:
        yield client


@asynccontextmanager
async def s3_client() -> AsyncIterator[Any]:
    async with _session().client("s3", **_client_kwargs()) as client:
        yield client


@asynccontextmanager
async def sqs_client() -> AsyncIterator[Any]:
    async with _session().client("sqs", **_client_kwargs()) as client:
        yield client


@asynccontextmanager
async def secrets_client() -> AsyncIterator[Any]:
    async with _session().client("secretsmanager", **_client_kwargs()) as client:
        yield client


@asynccontextmanager
async def cognito_idp_client() -> AsyncIterator[Any]:
    """Cognito User Pool admin API client.

    Used by the PostConfirmation Lambda to set `custom:org_id`,
    `custom:role`, `custom:team_id` on the user after row creation.
    """
    async with _session().client("cognito-idp", **_client_kwargs()) as client:
        yield client

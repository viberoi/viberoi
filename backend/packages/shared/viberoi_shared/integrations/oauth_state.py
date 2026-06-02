"""OAuth-flow state-parameter store.

The `state` query parameter on an OAuth authorize URL is the CSRF token
that ties a callback request back to the user/org that initiated it.

Slice 4 design:
  - Cryptographically random opaque token (`secrets.token_urlsafe(32)`)
  - Stored in Redis keyed `oauth:state:{token}`, value = JSON payload
    `{org_id, developer_id, provider, created_at}`
  - 10-minute TTL (OAuth flows typically complete in <60s)
  - Single-use guaranteed by atomic GETDEL on the callback side
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import orjson

from viberoi_shared.errors import VibeRoiError
from viberoi_shared.redis import get_client

_KEY_PREFIX = "oauth:state:"
STATE_TTL_SECONDS = 600  # 10 minutes


class OAuthStateError(VibeRoiError):
    code = "oauth_state_error"
    safe_message = "OAuth flow state is invalid or expired."


def generate_token() -> str:
    """Mint a fresh URL-safe random state token (256 bits)."""
    return secrets.token_urlsafe(32)


async def store(
    state: str,
    *,
    org_id: UUID,
    developer_id: UUID,
    provider: str,
    ttl: int = STATE_TTL_SECONDS,
) -> None:
    """Persist a state payload with TTL."""
    payload = orjson.dumps(
        {
            "org_id": str(org_id),
            "developer_id": str(developer_id),
            "provider": provider,
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
    )
    client = get_client()
    await client.set(f"{_KEY_PREFIX}{state}", payload.decode("utf-8"), ex=ttl)


async def consume(state: str) -> dict[str, Any]:
    """Atomically read + delete a state payload. Single-use.

    Raises `OAuthStateError` if the state is missing or expired.
    """
    if not state:
        raise OAuthStateError("Missing state parameter.")
    client = get_client()
    key = f"{_KEY_PREFIX}{state}"
    # Redis 6.2+ has GETDEL — atomic read-and-delete. The redis-py client
    # exposes it as .getdel().
    raw = await client.getdel(key)
    if raw is None:
        raise OAuthStateError("Unknown or expired state.")
    return orjson.loads(raw)

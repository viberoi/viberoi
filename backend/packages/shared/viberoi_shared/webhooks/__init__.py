"""Webhook HMAC verification per provider.

`verify(provider, headers, raw_body, secret)` — raises `Unauthorized` on
mismatch. Always pass RAW bytes (HMAC is byte-exact); never the parsed JSON.

V1 providers (Slice 4): github, gitlab, linear.
V2 providers (deferred): bitbucket, azure_devops, jira.

The `secret` is the webhook signing secret looked up from
`integration_oauth_tokens` and decrypted via `viberoi_shared.crypto`.
"""

from viberoi_shared.webhooks.verify import (
    GITHUB,
    GITLAB,
    GITLAB_TIMESTAMP_TOLERANCE_S,
    LINEAR,
    extract_delivery_id,
    verify,
    verify_github,
    verify_gitlab,
    verify_linear,
)

__all__ = [
    "GITHUB",
    "GITLAB",
    "GITLAB_TIMESTAMP_TOLERANCE_S",
    "LINEAR",
    "extract_delivery_id",
    "verify",
    "verify_github",
    "verify_gitlab",
    "verify_linear",
]

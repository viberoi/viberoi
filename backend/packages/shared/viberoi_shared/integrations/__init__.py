"""External-integration OAuth token storage.

Owns the `integration_oauth_tokens` table. Stores access + refresh
tokens KMS-encrypted (envelope), plus the per-org webhook signing
secret that `viberoi_shared.webhooks.verify(...)` uses.

Providers (V1): github, gitlab, jira, linear.

Tokens decrypt on demand inside the Integration service when calling
the external API; the webhook Lambda fetches and decrypts the
webhook signing secret per inbound webhook to verify HMAC.
"""

from viberoi_shared.integrations.models import IntegrationOAuthToken
from viberoi_shared.integrations.repository import (
    get_token_for_org,
    revoke_token,
    store_token,
)

__all__ = [
    "IntegrationOAuthToken",
    "get_token_for_org",
    "revoke_token",
    "store_token",
]

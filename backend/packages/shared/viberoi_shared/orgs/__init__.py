"""CRUD + ORM for orgs, developers, and RBAC.

Owns the domain-lock check (one org per email domain) and role assignment.
PII columns (email, names, GitHub username) are KMS-encrypted via
`viberoi_shared.crypto`.
"""

from viberoi_shared.orgs.models import Developer, Org, OrgToken, Team
from viberoi_shared.orgs.repository import (
    get_developer,
    get_developer_by_cognito_sub,
    get_developer_by_email_hash,
    get_org,
    get_org_by_domain,
    get_org_token,
    list_teams,
)

__all__ = [
    "Developer",
    "Org",
    "OrgToken",
    "Team",
    "get_developer",
    "get_developer_by_cognito_sub",
    "get_developer_by_email_hash",
    "get_org",
    "get_org_by_domain",
    "get_org_token",
    "list_teams",
]

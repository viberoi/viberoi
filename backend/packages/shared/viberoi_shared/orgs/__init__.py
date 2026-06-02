"""CRUD + ORM for orgs, developers, and RBAC.

Owns the domain-lock check (one org per email domain) and role assignment.
PII columns (email, names, GitHub username) are KMS-encrypted via
`viberoi_shared.crypto`.
"""

# CLAUDE.md — cognito_presignup Lambda

Cognito PreSignUp trigger. Last gate before a user account is created in
the user pool. Two enforcement points:

1. **Email-domain denylist.** Reject consumer email providers (gmail,
   yahoo, outlook, etc.). VibeROI is a team product, not a B2C product.
2. **One-org-per-domain.** If an `orgs` row already exists for the
   email's domain, reject the signup with "your team is already on
   VibeROI". The PostConfirmation Lambda attaches new signups to the
   existing org via the `/invite` flow (Slice 5+) rather than letting
   anyone create a second org for the same company.

## Failure surface

Cognito's PreSignUp trigger semantics: **raise an exception → signup is
denied**. The exception message is returned to the user verbatim (via
the Cognito SDK error). Keep messages short and user-facing.

## Why this is the right enforcement point

PostConfirmation is *after* the user has confirmed their email — too
late to politely turn them away. PreSignUp runs synchronously before
account creation, so we get clean rejection.

## What we don't do here

- No DB writes. The PostConfirmation Lambda owns row creation.
- No Cognito SDK calls. We're inside a trigger; we'd recurse.
- No logging of the raw email — log only `domain` and `decision`.

## Tests

Direct unit-test on `handler(event, context)`. The DB layer is mocked
via `monkeypatch.setattr(handler, "get_org_by_domain", ...)`. No real
Cognito, no real Postgres.

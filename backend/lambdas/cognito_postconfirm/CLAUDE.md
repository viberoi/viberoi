# CLAUDE.md — cognito_postconfirm Lambda

Cognito PostConfirmation trigger. Runs *after* the user confirms their
email (OTP per spec). Creates the org + developer rows and writes the
custom attributes (`org_id`, `role`, `team_id`) back to Cognito so
they end up in subsequent access tokens.

## Flow

```
1. lambda_auth.verify(event, context, expected_source="cognito:postconfirmation")
2. Parse: email + cognito_sub from event.userAttributes / event.userName
3. superuser_session():
     a. create_org_if_missing(domain, encrypted name)
     b. count_developers(org_id) → first user → role=OrgAdmin else Developer
     c. create_developer_if_missing(org_id, cognito_sub, role, encrypted email + email_hash)
4. cognito_idp.admin_update_user_attributes(
       UserPoolId, Username,
       UserAttributes=[{custom:org_id}, {custom:role}])
5. Return event (Cognito requires echo)
```

## Idempotency

Cognito does NOT guarantee exactly-once trigger delivery. Re-running
must produce the same final state:
- `create_org_if_missing` is an `ON CONFLICT DO NOTHING` upsert keyed on `domain`.
- `create_developer_if_missing` is keyed on `cognito_sub` (unique column).
- `admin_update_user_attributes` is idempotent by API contract.

## What we don't do here

- Don't fail the signup if the org already has the developer — return event normally.
- Don't decrypt or read the user's email back out for any reason.
- Don't send a welcome notification synchronously — that's the Notification service (enqueue via `viberoi_shared.notifications.enqueue`).

## Tests

Direct unit-test on `handler(event, context)`. DB + Cognito IDP are
mocked. We assert: row creation params, role-assignment logic
(first user vs subsequent), idempotency on re-invocation, custom
attribute update call shape.

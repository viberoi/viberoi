# CLAUDE.md — cognito_pre_token_gen Lambda

Cognito **Pre Token Generation v2.0** trigger. Runs on every token
issuance (sign-in, refresh) BEFORE Cognito assembles the access + ID
tokens. Returns claim overrides that get injected into both.

## Why this Lambda exists

By default, Cognito does NOT include `custom:*` attributes in the
**access** token — they only land in the ID token. Slice 5A picked
access tokens (smaller, less PII, AWS-recommended for backend auth),
so we need this Lambda to lift the custom attrs into the access token.

It also enforces a fail-closed contract: if `custom:developer_id`,
`custom:org_id`, or `custom:role` is missing from the user attributes
(which would happen if PostConfirmation hasn't run yet, or failed),
we return the event unchanged. The JWT verifier on the backend then
rejects the resulting token because those claims are required by
`CognitoClaims`.

## Event shape (v2.0)

```json
{
  "version": "2",
  "triggerSource": "TokenGeneration_Authentication",
  "userPoolId": "us-east-1_XXXX",
  "userName": "alice",
  "request": {
    "userAttributes": {
      "sub": "...",
      "email": "alice@example.com",
      "custom:org_id": "...",
      "custom:developer_id": "...",
      "custom:role": "...",
      "custom:team_id": "..."
    },
    "scopes": ["openid", "email", "profile"]
  },
  "response": {
    "claimsAndScopeOverrideDetails": null
  }
}
```

We populate `response.claimsAndScopeOverrideDetails.accessTokenGeneration.claimsToAddOrOverride`
with the four custom claims so they appear in the access token.

## Rules

- Never log raw user attributes (email is PII).
- Never make a DB call here — this Lambda runs on every token issuance
  and needs to be fast. The trust is: PostConfirmation set the attrs
  correctly; we just propagate them.
- Never fail-open. If a required attr is missing, return the event
  unchanged. The backend JWT verifier handles the rejection.

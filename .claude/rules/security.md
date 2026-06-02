---
description: Auth (Cognito), RLS, encryption (Argon2id + KMS+AES-256-GCM), webhook HMAC, secrets handling, no-content-stored. Non-negotiable.
---

# Security Rules

These rules are non-negotiable. Every PR is checked against them.

## Privacy principle (the product promise)

**Never store prompts, code, diffs, PR descriptions, commit-message bodies, or any user-generated content.**

We capture:
- Token counts, timestamps, model names, tool names
- File paths (not file contents)
- Branch names, commit hashes, LOC diffs (numbers only)
- Ticket IDs, sprint IDs, status

We do NOT capture, log, or transmit:
- Prompt text, completion text, chat history
- Source code, diff hunks, file contents
- PR/issue/commit message bodies (titles are OK for attribution Signal 5; bodies are not)

If you're tempted to write a field that holds user content — stop. Reframe as metadata or omit it.

## Auth — Cognito is the source of truth

- Cognito User Pool owns user identity and JWT issuance.
- Federation: Google native, GitHub via OIDC custom IdP.
- Signup: OTP only (no magic link on signup — spec amendment 2026-06-02).
- Login: magic link via Cognito CUSTOM_AUTH or OAuth provider.
- JWT validated on **every** dashboard request via `viberoi_shared.cognito.verify_jwt(token)`.
- JWKS cached in-process for 1h; refresh on cache miss.
- Expired or invalid token → 401, no retries, no leak of error detail.
- `org_id`, `role`, and `team_id` claims are Cognito custom attributes set by PostConfirmation Lambda.

## Cognito Lambda triggers — explicit checks

**PreSignUp Lambda:**
1. Reject if email domain is in `CONSUMER_EMAIL_DENYLIST` (gmail, yahoo, hotmail, outlook, icloud, etc.).
2. Lookup org by email domain in Postgres; if exists, reject signup with "your team is already on VibeROI" (one org per domain).
3. Assert `event.userPoolId` matches expected pool (defense-in-depth).

**PostConfirmation Lambda:**
1. Assert `event.userPoolId` matches expected pool.
2. Create `orgs` row (if first user for domain) or attach to existing org.
3. Create `developers` row with `org_id` and `role` (`OrgAdmin` for first user, `Developer` for invited).
4. Set Cognito custom attributes: `org_id`, `role`, `team_id`.
5. Idempotent — re-running on the same event must not duplicate rows.

## Row-Level Security (RLS) — Postgres-enforced

- Every table that holds org-scoped data has `org_id UUID NOT NULL` and an RLS policy: `org_id = current_setting('app.current_org_id')::uuid`.
- Every request handler must set `app.current_org_id` via `viberoi_shared.db.org_scoped_session(org_id)` before any DB call.
- The shared session helper sets the GUC and yields the AsyncSession. There is no other path to the DB from services.
- Even if a handler forgets to filter by org_id in SQL, RLS still prevents cross-org reads.

## Encryption — two primitives, two purposes

**Argon2id (hashing — one-way, verify-only):**
- Library: `argon2-cffi`.
- Params: `time_cost=3, memory_cost=64MB (65536 KiB), parallelism=4`.
- Used for: `org_token` storage, webhook signing secrets, any secret we only verify (never decrypt).
- Helper: `viberoi_shared.crypto.hash_secret(secret)` / `verify_secret(secret, hash)`.

**KMS + AES-256-GCM (envelope encryption — recoverable):**
- KMS CMK per environment (dev/staging/prod), automatic annual rotation + on-demand rotation.
- Envelope pattern: KMS encrypts the DEK; DEK encrypts the actual PII.
- Column shape: `(<field>_ciphertext BYTEA, <field>_key_version SMALLINT, <field>_iv BYTEA)`.
- Reads work across versions. A background job re-encrypts old rows on rotation.
- Helper: `viberoi_shared.crypto.encrypt_pii(value, context)` / `decrypt_pii(ciphertext, version, iv, context)`.
- `context` is the AAD (Additional Authenticated Data) — typically `f"org:{org_id}:field:{name}"`.
- Searchable PII: separate `<field>_hash` column = HMAC-SHA256(value, pepper) for lookup; full value stays encrypted.

**PII columns (encrypt by default):**
- `developers.email`, `full_name`, `github_username`, `machine_id`
- `orgs.billing_email`, `contact_phone`
- OAuth tokens (GitHub App tokens, Jira OAuth tokens)
- Slack/Teams webhook URLs
- Invitation tokens (these are *hashed*, not encrypted — verification only)

**Plaintext-safe columns (never PII):**
- IDs (UUID), `org_id` foreign keys, timestamps, roles, status enums, counts, hashes of PII.

## Webhook HMAC verification

Every webhook Lambda:
1. Captures raw body **before** JSON parse (HMAC is over bytes).
2. Reads signature header (`X-Hub-Signature-256` for GitHub, `X-Gitlab-Token` for GitLab, etc.).
3. Calls `viberoi_shared.webhooks.verify(provider, headers, raw_body)`.
4. On failure: returns 401 immediately. No retry, no detail in response.
5. On success: pushes to SQS `webhook_events` queue and returns 200.

## Lambda auth — explicit per type

Every Lambda's first line of logic:

```python
from viberoi_shared.lambda_auth import verify

def handler(event, context):
    verify(event, context, expected_source="<source>")
    ...
```

| Lambda type | `expected_source` | What `verify` checks |
|---|---|---|
| Webhook receiver | `"webhook:<provider>"` | HMAC signature on raw body |
| Cognito PreSignUp | `"cognito:presignup"` | `event.userPoolId` matches env, `event.triggerSource == "PreSignUp_SignUp"` |
| Cognito PostConfirmation | `"cognito:postconfirmation"` | same + `triggerSource == "PostConfirmation_ConfirmSignUp"` |
| EventBridge cron | `"eventbridge:<rule>"` | `event.source == "aws.events"`, `event.resources` contains expected rule ARN |

## Secrets handling

- **Production:** all secrets from AWS Secrets Manager via `viberoi_shared.secrets.get(key)`. Cached in-process 5 min.
- **Local dev:** `.env.local` (gitignored), loaded by `viberoi_shared.secrets` when `VIBEROI_ENV=dev`.
- **Never** in code, environment variables in Dockerfiles, plaintext config files, or git history.
- IAM roles, not access keys, for all AWS service-to-service calls.

## Org token (agent → backend)

- Generated at agent install (one per developer machine).
- Stored hashed (Argon2id) on backend.
- Sent in every `/ingest/*` request as `Authorization: VibeROI <token>` header.
- Backend looks up by `developer_id` (also in header), then verifies hash.
- Rotation: `POST /agent/rotate-token` issues new token, old one revoked after grace period.

## Logging — what NEVER goes in logs

- Token values, JWT bodies, raw HMAC signatures
- PII (emails, names, GitHub usernames)
- Any captured user content
- Secrets, API keys, OAuth tokens
- Full session payloads (log session_id + org_id + outcome only)

Use the shared logger which scrubs known PII fields by default. If you're tempted to log something sensitive for debugging — use a metric or a counter instead.

## Crypto invariants for code review

If any of these appear in a service file (not in `viberoi_shared/crypto`), the PR is blocked:
- `import boto3` + `kms` client (only `viberoi_shared.crypto` may touch KMS)
- `Cipher(`, `AES.new(`, raw `cryptography.hazmat`
- `argon2`, `bcrypt`, `hashlib.pbkdf2`
- IV/nonce generation (`secrets.token_bytes` for crypto purposes)
- Pepper / salt definitions

All of these belong in `viberoi_shared.crypto` only.

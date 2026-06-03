# cognito

User pool + app client + hosted-UI domain.

## Resources

| Resource | Notes |
|---|---|
| `aws_cognito_user_pool.this` | ESSENTIALS tier (free under 50k MAU). Email sign-in, custom attrs `org_id` / `developer_id` / `role` / `team_id`. MFA off in V1. |
| `aws_cognito_user_pool_domain.this` | Cognito-managed subdomain. Random hex suffix avoids global-name collisions on recreate. |
| `aws_cognito_identity_provider.google` | Optional — created only when both `google_client_id` and `google_client_secret` are set. |
| `aws_cognito_identity_provider.github` | Optional — same pattern. OIDC against `github.com/login/oauth`. |
| `aws_cognito_user_pool_client.spa` | Public SPA (no secret). SRP + refresh only. Reads/writes the custom attrs. |
| `aws_lambda_permission.*` | Conditional — only when trigger ARNs are wired (6D). |

## Inputs

| name | default | notes |
|---|---|---|
| `callback_urls` | `["http://localhost:5173/auth/callback"]` | Add your real frontend URL once wired. |
| `logout_urls` | `["http://localhost:5173/"]` | |
| `lambda_pre_signup_arn` | null | Wired in 6D once Lambda exists. |
| `lambda_post_confirmation_arn` | null | Same. |
| `lambda_pre_token_generation_arn` | null | Same. Required for custom claims in access tokens. |
| `google_client_id` / `google_client_secret` | `""` | Both empty → no Google IdP. |
| `github_oidc_client_id` / `github_oidc_client_secret` | `""` | Both empty → no GitHub IdP. |
| `access_token_validity_hours` | 1 | |
| `refresh_token_validity_days` | 30 | |

## Outputs

`user_pool_id`, `user_pool_arn`, `user_pool_endpoint` (the `iss` claim),
`spa_client_id`, `hosted_ui_domain` (full FQDN), `hosted_ui_domain_prefix`.

Wire these into Python settings:
- `cognito_user_pool_id` ← `user_pool_id`
- `cognito_region` ← provider region (us-east-1)
- `cognito_app_client_id` ← `spa_client_id`

And into the frontend Cognito SDK config:
- `userPoolId` ← `user_pool_id`
- `userPoolWebClientId` ← `spa_client_id`
- `oauth.domain` ← `hosted_ui_domain`

## Cost

ESSENTIALS tier is free up to 50k MAU. Above that ~$0.0055/MAU.

## Two-phase trigger wiring

6C creates the pool without `lambda_config`. 6D ships the Lambda
container images + IAM roles, then re-applies the env to plug their
ARNs into this module — the conditional `dynamic "lambda_config"`
block then writes the triggers without any cross-module trickery.

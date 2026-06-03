# cognito_custom_domain

Attaches a custom domain to an existing Cognito user pool.

Cognito requires:
- ACM cert in us-east-1 covering the domain.
- Cert must be `ISSUED` (not pending) at apply time.
- Parent domain (apex) must resolve — true for any owned domain.

After apply, CNAME `<domain>` → `<cloudfront_distribution>` at Hostinger.

## Apply ordering

This module is a separate piece because the cert must be validated
*before* you apply it. Workflow:

1. Apply `modules/acm_cert` — cert in PENDING.
2. Add validation CNAMEs at Hostinger.
3. Wait for cert to flip to `ISSUED` (~30 min).
4. Apply this module.

## Inputs

| name | notes |
|---|---|
| `user_pool_id` | from modules/cognito |
| `domain` | e.g. `auth.viberoi.io` |
| `certificate_arn` | ACM us-east-1 cert covering `domain` |

## Outputs

`cloudfront_distribution`, `domain`.

# cloudfront_frontend

CloudFront distribution in front of the frontend S3 bucket.

- Origin Access Control (OAC) — bucket reads only from this dist.
- SPA: 403/404 → `/index.html` 200 (Vite + React Router handles routes).
- HTTPS only — viewer protocol policy `redirect-to-https`.
- Price class 100 (US/EU edges only) — cheapest.
- Managed cache policy: `CachingOptimized` (the well-known UUID).

## Custom domain (optional)

To serve from `app.<your-domain>`:

1. Provide `aliases = ["app.viberoi.io"]`.
2. Provide `certificate_arn` — must be ACM cert in **us-east-1**
   (CloudFront requirement, locked).
3. After apply, CNAME `app.viberoi.io` → `<distribution_domain_name>`
   at Hostinger.

Without aliases + cert, the distribution serves on `<id>.cloudfront.net`.

## Inputs

| name | notes |
|---|---|
| `frontend_bucket_id` | from modules/s3 |
| `frontend_bucket_regional_domain_name` | from modules/s3 |
| `frontend_bucket_arn` | from modules/s3 |
| `aliases` | custom-domain names |
| `certificate_arn` | required if aliases is non-empty |

## Outputs

`distribution_id`, `distribution_domain_name`, `distribution_hosted_zone_id`, `distribution_arn`.

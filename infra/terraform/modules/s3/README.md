# s3

Three platform buckets per env. All public-blocked, all versioned.

| Bucket | SSE | Purpose | Lifecycle |
|---|---|---|---|
| `${prefix}-org-data-${acct}` | KMS | Raw session JSONL from agent | IA at 30d, Glacier at 90d, expire at 365d |
| `${prefix}-backups-${acct}` | KMS | RDS logical backups | none (managed by snapshot policy) |
| `${prefix}-frontend-${acct}` | AES256 | Vite build for CloudFront | none |

Frontend is AES256 (not KMS) so CloudFront's Origin Access Control can
read without a key-policy carve-out.

> ⚠️ The Python ingest code currently hardcodes `RAW_BUCKET = "viberoi-org-data"`.
> The bucket actually created is `${prefix}-org-data-${account_id}` for
> global uniqueness. Either rename the bucket in the module to match
> the constant, or change the Python side to read from settings — TBD
> when we wire ECS task envs in 6D.

## Inputs

| name | notes |
|---|---|
| `project`, `env` | name prefix |
| `kms_key_arn` | from modules/kms |
| `account_id` | suffix for bucket-name uniqueness |
| `raw_landing_retention_days` | default 365 |

## Outputs

Bucket ids + ARNs + the frontend regional domain (for CloudFront).

## S3 → SQS notification

NOT in this module. Wired in the env composition because the SQS queue
arn is needed and we want the dependency direction explicit.

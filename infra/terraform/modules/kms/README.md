# kms

Single KMS CMK per env for envelope-encrypted PII.

Used by `viberoi_shared.crypto.envelope` for RDS PII columns, OAuth
tokens, Slack webhook URLs, etc. Also wired into RDS storage SSE, S3
SSE-KMS, and SQS queue encryption.

## Inputs

| name | default | notes |
|---|---|---|
| `project` | `viberoi` | name prefix |
| `env` | — | dev/staging/prod |
| `alias` | `viberoi-pii` | alias short name. Final = `alias/<alias>`. **Must match `settings.kms_key_id`** in Python config. |
| `deletion_window_days` | `30` | wait window before key is actually deleted. |
| `enable_key_rotation` | `true` | annual material rotation. Decrypt across versions stays transparent. |
| `additional_iam_arns` | `[]` | task / Lambda execution roles that get encrypt+decrypt. Wire in env composition once those exist (6D+). |

## Outputs

`key_id`, `key_arn`, `alias_name`.

## Cost

~$1/mo per key + per-request usage charges.

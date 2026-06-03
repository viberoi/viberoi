# log_groups

One CloudWatch log group per service or Lambda.

Path: `/viberoi/<env>/<kind>/<short-name>`.

| Input | Notes |
|---|---|
| `service_names` | list of short names — one log group each |
| `log_kind` | `ecs` or `lambda` |
| `retention_days` | default 30 |
| `kms_key_arn` | reserved — see KMS-policy note below |

## KMS note

CloudWatch Logs requires the encrypting CMK's policy to grant the
`logs.<region>.amazonaws.com` service principal `kms:Encrypt*` /
`kms:Decrypt*` / `kms:GenerateDataKey*`. The env CMK in `modules/kms`
doesn't include that today, so this module leaves logs unencrypted
for now. Revisit when we extend the KMS policy.

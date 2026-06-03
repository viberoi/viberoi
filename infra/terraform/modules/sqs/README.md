# sqs

Four standard queues + DLQs.

| Queue | Producer | Consumer |
|---|---|---|
| `session_ingest` | S3 raw-landing bucket events | Worker service |
| `webhook_events` | webhook_receiver Lambda | Worker service |
| `backfill_jobs` | Integration service (orchestrator + /sync route) | Integration consumer |
| `notification_jobs` | viberoi_shared.notifications.enqueue | Notification consumer |

Each queue:
- KMS-SSE with the env CMK
- Visibility 30s
- Retention 14d (AWS max)
- Redrive to `<name>-dlq` after 3 receives

`session_ingest` has an additional queue policy allowing the
raw-landing S3 bucket (and only that bucket) to publish events.

## Inputs

| name | default | notes |
|---|---|---|
| `project`, `env` | | name prefix |
| `kms_key_arn` | | from modules/kms |
| `raw_landing_bucket_arn` | | from modules/s3 |
| `visibility_timeout_seconds` | 30 | match the Python long-poll defaults |
| `message_retention_seconds` | 1_209_600 (14d) | AWS max |
| `max_receive_count` | 3 | DLQ trigger |

## Outputs

`queue_arns`, `queue_urls`, `dlq_arns` — all keyed by short name.

## Naming note

Queues are NOT env-prefixed because `viberoi_shared.sqs.publish` looks
up by bare name (`"notification_jobs"`, not `"viberoi-dev-notification_jobs"`).
Each env therefore needs its own AWS account or some other isolation.
We use one account with separate envs ramping later, so queue names
collide unless one env applies at a time. (TODO: add env-prefix
support both sides for true multi-env-per-account.)

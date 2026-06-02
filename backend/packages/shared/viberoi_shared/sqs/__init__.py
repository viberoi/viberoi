"""SQS publish / consume helpers.

Standard queues: `session_ingest`, `webhook_events`, `backfill_jobs`,
`notification_jobs`. All have DLQs configured in Terraform; helpers
respect visibility timeout + max-retry semantics.
"""

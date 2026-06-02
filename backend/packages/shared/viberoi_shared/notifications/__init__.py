"""Notification enqueue (one-way; services never deliver synchronously).

Services call `enqueue(org_id, channel, template, payload, deliver_after=None)`
which writes to SQS `notification_jobs`. The Notification Service is the
only consumer — it owns templates, retries, rate limiting, channel routing.

If you're tempted to call Slack / Teams / SES directly: don't. Enqueue.
"""

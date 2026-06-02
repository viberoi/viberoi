"""Webhook receiver Lambda.

Verifies HMAC, publishes raw payload to SQS `webhook_events`, returns 200.
See CLAUDE.md.
"""

__version__ = "0.1.0"

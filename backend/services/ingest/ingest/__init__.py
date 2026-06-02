"""VibeROI Ingest service.

Receives session pushes from the Go agent, validates HMAC + org_token,
writes raw payloads to S3 raw-landing, returns 202 immediately.
"""

__version__ = "0.1.0"

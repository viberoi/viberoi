"""VibeROI Worker service.

Consumes S3 events from SQS session_ingest, runs attribution, persists
session rows. See CLAUDE.md.
"""

__version__ = "0.1.0"

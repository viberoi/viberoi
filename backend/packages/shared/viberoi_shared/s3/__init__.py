"""S3 read/write for raw-landing buckets and per-org exports.

Layout: `vibeROI-org-data/orgs/{org_id}/sessions/{date}/{session}.json.gz`.
SSE encryption is mandatory; helpers refuse unencrypted PUTs.
"""

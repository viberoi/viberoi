"""boto3 / aioboto3 client factories.

Services NEVER `import boto3` directly (ruff banned-api enforces).
They import a typed client factory from here, which:
  - applies retry config and timeouts uniformly
  - uses IAM role credentials in prod
  - points at LocalStack in dev (`aws_endpoint_url` in settings)
"""

from viberoi_shared.aws.clients import kms_client, s3_client, secrets_client, sqs_client

__all__ = ["kms_client", "s3_client", "secrets_client", "sqs_client"]

"""boto3 / aioboto3 client factories.

Services NEVER `import boto3` directly (ruff banned-api enforces).
They import a typed client factory from here, which:
  - applies retry config and timeouts uniformly
  - uses IAM role credentials in prod
  - points at LocalStack in dev (`AWS_ENDPOINT_URL` env var)
"""

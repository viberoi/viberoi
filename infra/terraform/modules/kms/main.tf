# KMS CMK for envelope-encrypted PII.
#
# Used by:
#   - viberoi_shared.crypto.envelope (RDS PII columns, OAuth tokens,
#     notification webhook URLs, KMS-SSE on S3 + SQS)
#   - RDS storage encryption
#   - S3 SSE-KMS
#   - SQS queue encryption
#
# Annual rotation is enabled — AWS swaps the underlying material once
# a year. Decrypt across versions is automatic, so old ciphertexts
# (stored in `*_key_version=1`) keep reading. Bump `key_version` in
# our column shape only when WE want to force a re-encryption pass.

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "kms"
    },
    var.tags,
  )
}

resource "aws_kms_key" "this" {
  description             = "${local.prefix} — envelope encryption for PII at rest"
  key_usage               = "ENCRYPT_DECRYPT"
  deletion_window_in_days = var.deletion_window_days
  enable_key_rotation     = var.enable_key_rotation

  # Allow root + the additional principals to use the key. Each service's
  # task role is added to `additional_iam_arns` by the env composition.
  # Use a default policy + IAM-based access; the explicit policy here
  # keeps the key explicit-deny by default for the rest of the account.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "EnableRootAccountAccess"
          Effect = "Allow"
          Principal = {
            AWS = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"
          }
          Action   = "kms:*"
          Resource = "*"
        }
      ],
      length(var.additional_iam_arns) > 0 ? [
        {
          Sid    = "AllowServicePrincipals"
          Effect = "Allow"
          Principal = {
            AWS = var.additional_iam_arns
          }
          Action = [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:GenerateDataKey",
            "kms:GenerateDataKey*",
            "kms:DescribeKey",
          ]
          Resource = "*"
        }
      ] : []
    )
  })

  tags = merge(local.common_tags, { Name = "${local.prefix}-pii-cmk" })
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.alias}"
  target_key_id = aws_kms_key.this.id
}

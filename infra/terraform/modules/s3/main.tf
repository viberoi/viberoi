# Platform S3 buckets.
#
# Three buckets per env:
#   1. org-data — raw landing for agent session pushes. Bucket
#      notification → SQS session_ingest fan-out. Wired in env file.
#   2. backups — RDS automated snapshots' destination if logical backups
#      are emitted via cron.
#   3. frontend — Vite build output. CloudFront origin in 6E.
#
# All SSE-KMS, versioned, public-blocked. Bucket names suffixed with
# the AWS account id for global uniqueness.

locals {
  prefix  = "${var.project}-${var.env}"
  suffix  = var.account_id
  raw     = "${local.prefix}-org-data-${local.suffix}"
  backups = "${local.prefix}-backups-${local.suffix}"
  fe      = "${local.prefix}-frontend-${local.suffix}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "s3"
    },
    var.tags,
  )
}

# ── Helper: standard bucket hardening ──────────────────────────────────────
# Re-used per bucket. Each block lives next to the bucket resource it
# guards so Terraform's drift detection is straightforward.

# ── org-data — raw landing ─────────────────────────────────────────────────
resource "aws_s3_bucket" "org_data" {
  bucket        = local.raw
  force_destroy = false
  tags          = merge(local.common_tags, { Name = local.raw, Purpose = "raw-landing" })
}

resource "aws_s3_bucket_public_access_block" "org_data" {
  bucket                  = aws_s3_bucket.org_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "org_data" {
  bucket = aws_s3_bucket.org_data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "org_data" {
  bucket = aws_s3_bucket.org_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "org_data" {
  bucket = aws_s3_bucket.org_data.id

  rule {
    id     = "expire-raw-sessions"
    status = "Enabled"

    filter {
      prefix = "orgs/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = var.raw_landing_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# ── backups ────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "backups" {
  bucket        = local.backups
  force_destroy = false
  tags          = merge(local.common_tags, { Name = local.backups, Purpose = "backups" })
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ── frontend ───────────────────────────────────────────────────────────────
# Hosting via CloudFront (6E). Bucket itself stays private; CF accesses
# via OAC. SSE-S3 (AES256) — CF cannot read SSE-KMS unless we share key
# policy with the CF service principal, which adds complexity.
resource "aws_s3_bucket" "frontend" {
  bucket        = local.fe
  force_destroy = false
  tags          = merge(local.common_tags, { Name = local.fe, Purpose = "frontend" })
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  versioning_configuration {
    status = "Enabled"
  }
}

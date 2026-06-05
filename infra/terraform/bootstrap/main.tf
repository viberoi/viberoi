# Terraform bootstrap - state bucket + lock table.
#
# Apply ONCE per AWS account using local state. After it succeeds, every
# other Terraform module uses the bucket created here as remote state.
#
# Chicken-and-egg: this module creates the bucket that holds remote state,
# so its own state intentionally stays local. See README.md.

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # NOT configured: backend "s3" - this module creates that bucket.
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "bootstrap"
    }
  }
}

# ─── State bucket ───────────────────────────────────────────────────────
resource "aws_s3_bucket" "tf_state" {
  bucket = "${var.project}-tf-state-${var.account_id}"
}

resource "aws_s3_bucket_versioning" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── Lock table ─────────────────────────────────────────────────────────
resource "aws_dynamodb_table" "tf_lock" {
  name         = "${var.project}-tf-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

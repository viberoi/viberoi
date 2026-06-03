# One ECR repo per service / Lambda.
#
# Repo URIs: <acct>.dkr.ecr.<region>.amazonaws.com/<prefix>-<env>-<name>
# GitHub Actions pushes `:<commit-sha>` and `:latest` per service in 6F.
#
# Lifecycle: keep the 30 newest tagged images, expire untagged after
# 14 days. Image scanning on push catches CVEs in deploys.

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "ecr"
    },
    var.tags,
  )
}

resource "aws_ecr_repository" "this" {
  for_each = toset(var.repo_names)

  name                 = "${local.prefix}-${each.key}"
  image_tag_mutability = "IMMUTABLE"

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.kms_key_arn
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, { Name = "${local.prefix}-${each.key}" })
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each = aws_ecr_repository.this

  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep newest ${var.keep_tagged_count} tagged images."
        selection = {
          tagStatus      = "tagged"
          tagPatternList = ["*"]
          countType      = "imageCountMoreThan"
          countNumber    = var.keep_tagged_count
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Expire untagged after ${var.expire_untagged_after_days} days."
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.expire_untagged_after_days
        }
        action = { type = "expire" }
      },
    ]
  })
}

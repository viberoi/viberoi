# Container-image Lambda.
#
# Used for: webhook_receiver, cognito_presignup, cognito_postconfirm,
# and the new cognito_pre_token_generation (added in this slice).
#
# Each Lambda pulls a tagged image from ECR. The execution role is
# created externally (modules/iam_task_role) so service-specific
# scoped policies live there, not buried in this module.

locals {
  prefix = "${var.project}-${var.env}-${var.name}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "container_lambda"
      Service   = var.name
    },
    var.tags,
  )
}

# Log group - we own it when caller doesn't pass one in. Most consumers
# in this stack pass log_group_name from modules/log_groups, but
# providing a fallback keeps the module standalone for tests.
resource "aws_cloudwatch_log_group" "this" {
  count             = var.log_group_name == null ? 1 : 0
  name              = "/aws/lambda/${local.prefix}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, { Name = "/aws/lambda/${local.prefix}" })
}

# Lambda function backed by an ECR image.
resource "aws_lambda_function" "this" {
  function_name = local.prefix
  role          = var.role_arn

  package_type = "Image"
  image_uri    = var.image_uri

  timeout     = var.timeout_seconds
  memory_size = var.memory_mb

  environment {
    variables = var.env_vars
  }

  dynamic "vpc_config" {
    for_each = length(var.vpc_subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, { Name = local.prefix })

  # Image URI updates flow through Terraform; logs config flows through
  # the dedicated log_group resource above (or the env composition).
  # Don't ignore environment - env-var changes ARE deploys.
  depends_on = [aws_cloudwatch_log_group.this]
}

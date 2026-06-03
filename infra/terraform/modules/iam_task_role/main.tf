# Per-service IAM task role.
#
# Returns two roles per call:
#   - execution_role — used by ECS to pull the image, write to
#     CloudWatch logs, and decrypt Secrets Manager refs in the task
#     definition's `secrets` block.
#   - task_role — used by the *running container* for KMS, SQS, S3,
#     Cognito, etc. Scoped per `service_name`.
#
# Lambdas reuse this module by passing `assume_role_service = "lambda.amazonaws.com"`
# — the same scoped policy shape applies.

locals {
  prefix = "${var.project}-${var.env}-${var.service_name}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "iam_task_role"
      Service   = var.service_name
    },
    var.tags,
  )
}

# ── Execution role ─────────────────────────────────────────────────────────
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = [var.assume_role_service]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.prefix}-execution"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = local.common_tags
}

# Standard ECS task-execution policy: ECR pull + CloudWatch logs write.
resource "aws_iam_role_policy_attachment" "execution_basic" {
  count      = var.assume_role_service == "ecs-tasks.amazonaws.com" ? 1 : 0
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Standard Lambda execution policy: log group write.
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  count      = var.assume_role_service == "lambda.amazonaws.com" ? 1 : 0
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda inside the VPC needs an additional VPC-access policy so it
# can attach ENIs to subnets.
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count      = var.assume_role_service == "lambda.amazonaws.com" ? 1 : 0
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Both ECS exec and Lambda exec need GetSecretValue on the secrets
# the task references in its `secrets` block (ECS) or fetches at
# runtime (Lambda).
data "aws_iam_policy_document" "execution_secrets" {
  count = length(var.secret_arns) > 0 ? 1 : 0

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = var.secret_arns
  }

  statement {
    actions   = ["kms:Decrypt"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  count  = length(var.secret_arns) > 0 ? 1 : 0
  name   = "${local.prefix}-execution-secrets"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_secrets[0].json
}

# ── Task role (for the running container / Lambda) ─────────────────────────
resource "aws_iam_role" "task" {
  name               = "${local.prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = local.common_tags
}

# Aggregate scoped policy — everything the service can do at runtime.
data "aws_iam_policy_document" "task" {
  # KMS — always (every service touches encrypted columns at some point).
  statement {
    sid    = "KMSEnvelope"
    effect = "Allow"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]
    resources = [var.kms_key_arn]
  }

  # Secrets Manager — runtime reads (`viberoi_shared.secrets.get`).
  dynamic "statement" {
    for_each = length(var.secret_arns) > 0 ? [1] : []
    content {
      sid       = "SecretsRead"
      effect    = "Allow"
      actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
      resources = var.secret_arns
    }
  }

  # SQS publish.
  dynamic "statement" {
    for_each = length(var.sqs_send_arns) > 0 ? [1] : []
    content {
      sid       = "SQSSend"
      effect    = "Allow"
      actions   = ["sqs:SendMessage", "sqs:GetQueueUrl", "sqs:GetQueueAttributes"]
      resources = var.sqs_send_arns
    }
  }

  # SQS consume.
  dynamic "statement" {
    for_each = length(var.sqs_receive_arns) > 0 ? [1] : []
    content {
      sid    = "SQSConsume"
      effect = "Allow"
      actions = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueUrl",
        "sqs:GetQueueAttributes",
        "sqs:ChangeMessageVisibility",
      ]
      resources = var.sqs_receive_arns
    }
  }

  # S3 read (bucket + objects).
  dynamic "statement" {
    for_each = length(var.s3_read_arns) > 0 ? [1] : []
    content {
      sid       = "S3ListBucket"
      effect    = "Allow"
      actions   = ["s3:ListBucket"]
      resources = var.s3_read_arns
    }
  }
  dynamic "statement" {
    for_each = length(var.s3_read_arns) > 0 ? [1] : []
    content {
      sid       = "S3Read"
      effect    = "Allow"
      actions   = ["s3:GetObject"]
      resources = [for a in var.s3_read_arns : "${a}/*"]
    }
  }

  # S3 write (object PUT/DELETE).
  dynamic "statement" {
    for_each = length(var.s3_write_arns) > 0 ? [1] : []
    content {
      sid       = "S3ListWriteBucket"
      effect    = "Allow"
      actions   = ["s3:ListBucket"]
      resources = var.s3_write_arns
    }
  }
  dynamic "statement" {
    for_each = length(var.s3_write_arns) > 0 ? [1] : []
    content {
      sid       = "S3Write"
      effect    = "Allow"
      actions   = ["s3:PutObject", "s3:DeleteObject"]
      resources = [for a in var.s3_write_arns : "${a}/*"]
    }
  }

  # Cognito admin — only the PostConfirmation Lambda needs this.
  dynamic "statement" {
    for_each = var.cognito_user_pool_arn != null ? [1] : []
    content {
      sid       = "CognitoAdminUpdate"
      effect    = "Allow"
      actions   = ["cognito-idp:AdminUpdateUserAttributes", "cognito-idp:AdminGetUser"]
      resources = [var.cognito_user_pool_arn]
    }
  }
}

resource "aws_iam_role_policy" "task" {
  name   = "${local.prefix}-task-scoped"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task.json
}

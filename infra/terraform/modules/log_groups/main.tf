# One log group per service / Lambda.
#
# Path: /viberoi/<env>/<kind>/<name>
#   kind = ecs → ECS Fargate task logs (awslogs driver)
#   kind = lambda → Lambda invocation logs (Lambda runtime auto-writes)
#
# KMS-encrypted with the env CMK. The CMK's policy must allow
# `logs.<region>.amazonaws.com` to encrypt - modules/kms doesn't grant
# that by default, so for now we leave logs unencrypted in dev to avoid
# coupling. Re-enable when ready by passing a kms_key_arn whose policy
# includes the logs service principal.

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "log_groups"
    },
    var.tags,
  )
}

resource "aws_cloudwatch_log_group" "this" {
  for_each = toset(var.service_names)

  name              = "/viberoi/${var.env}/${var.log_kind}/${each.key}"
  retention_in_days = var.retention_days

  # KMS-SSE only if the key's policy allows the logs service principal.
  # Leave null in V1; revisit when we wire logs ↔ KMS together.
  # kms_key_id = var.kms_key_arn

  tags = merge(local.common_tags, { Name = "/viberoi/${var.env}/${var.log_kind}/${each.key}" })
}

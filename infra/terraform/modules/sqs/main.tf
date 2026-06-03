# Four standard queues + DLQs per env.
#
# Queue names MUST exactly match what application code passes to
# viberoi_shared.sqs.publish(<name>, ...) since the queue URL is looked
# up by name. Don't prefix here — the Python code uses bare names.

locals {
  prefix = "${var.project}-${var.env}"

  # Bare queue names — no env prefix, see comment above.
  queues = {
    session_ingest    = "session_ingest"
    webhook_events    = "webhook_events"
    backfill_jobs     = "backfill_jobs"
    notification_jobs = "notification_jobs"
  }

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "sqs"
    },
    var.tags,
  )
}

# ── Dead-letter queues ─────────────────────────────────────────────────────
resource "aws_sqs_queue" "dlq" {
  for_each = local.queues

  name                      = "${each.value}-dlq"
  message_retention_seconds = var.message_retention_seconds
  kms_master_key_id         = var.kms_key_arn

  tags = merge(local.common_tags, { Name = "${each.value}-dlq", Role = "dlq" })
}

# ── Main queues ────────────────────────────────────────────────────────────
resource "aws_sqs_queue" "main" {
  for_each = local.queues

  name                       = each.value
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  kms_master_key_id          = var.kms_key_arn

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = merge(local.common_tags, { Name = each.value, Role = "main" })
}

# ── Allow S3 raw-landing bucket to publish to session_ingest ───────────────
# The bucket's NotificationConfiguration (wired in the env file) is the
# trigger; this policy is what makes the queue accept the publish.
data "aws_iam_policy_document" "session_ingest_from_s3" {
  statement {
    sid    = "AllowS3RawLandingPublish"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }

    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.main["session_ingest"].arn]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [var.raw_landing_bucket_arn]
    }
  }
}

resource "aws_sqs_queue_policy" "session_ingest" {
  queue_url = aws_sqs_queue.main["session_ingest"].id
  policy    = data.aws_iam_policy_document.session_ingest_from_s3.json
}

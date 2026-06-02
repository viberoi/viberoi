#!/bin/bash
# Bootstraps LocalStack with the AWS resources VibeROI expects in dev.
# Runs automatically inside the localstack container on startup
# (mounted to /etc/localstack/init/ready.d/init.sh).

set -e
echo "[viberoi] Bootstrapping LocalStack..."

# ── KMS — one CMK for PII envelope encryption ────────────────────────────────
if ! awslocal kms list-aliases --query "Aliases[?AliasName=='alias/viberoi-pii']" --output text | grep -q viberoi-pii; then
    KEY_ID=$(awslocal kms create-key \
        --description "VibeROI PII envelope key (dev)" \
        --tags TagKey=Project,TagValue=viberoi \
        --query 'KeyMetadata.KeyId' --output text)
    awslocal kms create-alias \
        --alias-name alias/viberoi-pii \
        --target-key-id "$KEY_ID"
    echo "[viberoi] Created KMS key: $KEY_ID (alias/viberoi-pii)"
fi

# ── S3 buckets ──────────────────────────────────────────────────────────────
for bucket in viberoi-org-data viberoi-kiro-sync viberoi-backups; do
    if ! awslocal s3 ls "s3://$bucket" >/dev/null 2>&1; then
        awslocal s3 mb "s3://$bucket"
        awslocal s3api put-bucket-encryption \
            --bucket "$bucket" \
            --server-side-encryption-configuration \
            '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
        echo "[viberoi] Created S3 bucket: $bucket (SSE enabled)"
    fi
done

# ── SQS queues — each main queue gets a DLQ with maxReceiveCount=3 ──────────
declare -A QUEUE_ARNS
for queue in session_ingest webhook_events backfill_jobs notification_jobs; do
    awslocal sqs create-queue --queue-name "${queue}_dlq" >/dev/null
    DLQ_URL=$(awslocal sqs get-queue-url --queue-name "${queue}_dlq" --query QueueUrl --output text)
    DLQ_ARN=$(awslocal sqs get-queue-attributes \
        --queue-url "$DLQ_URL" \
        --attribute-names QueueArn \
        --query 'Attributes.QueueArn' --output text)
    awslocal sqs create-queue \
        --queue-name "$queue" \
        --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\",\"VisibilityTimeout\":\"30\"}" \
        >/dev/null
    QUEUE_URL=$(awslocal sqs get-queue-url --queue-name "$queue" --query QueueUrl --output text)
    QUEUE_ARN=$(awslocal sqs get-queue-attributes \
        --queue-url "$QUEUE_URL" \
        --attribute-names QueueArn \
        --query 'Attributes.QueueArn' --output text)
    QUEUE_ARNS[$queue]=$QUEUE_ARN
    echo "[viberoi] Created SQS queue: $queue (+ ${queue}_dlq)"
done

# ── S3 → SQS event notification ─────────────────────────────────────────────
# When a session lands in viberoi-org-data, fire an event to session_ingest.
# Worker long-polls session_ingest and pulls the S3 object on each event.
# Filter: only orgs/*.json.gz (the canonical raw-landing key shape).
awslocal s3api put-bucket-notification-configuration \
    --bucket viberoi-org-data \
    --notification-configuration "{
        \"QueueConfigurations\": [
            {
                \"QueueArn\": \"${QUEUE_ARNS[session_ingest]}\",
                \"Events\": [\"s3:ObjectCreated:*\"],
                \"Filter\": {
                    \"Key\": {
                        \"FilterRules\": [
                            {\"Name\": \"prefix\", \"Value\": \"orgs/\"},
                            {\"Name\": \"suffix\", \"Value\": \".json.gz\"}
                        ]
                    }
                }
            }
        ]
    }"
echo "[viberoi] Wired S3 event notification: viberoi-org-data → session_ingest"

# ── Secrets Manager — dev pepper for HMAC lookups ───────────────────────────
if ! awslocal secretsmanager describe-secret --secret-id viberoi/dev/lookup_pepper >/dev/null 2>&1; then
    awslocal secretsmanager create-secret \
        --name viberoi/dev/lookup_pepper \
        --description "Deterministic HMAC pepper for searchable encrypted columns (dev only)" \
        --secret-string '{"pepper":"dev-pepper-not-for-prod-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}' \
        >/dev/null
    echo "[viberoi] Created secret: viberoi/dev/lookup_pepper"
fi

echo "[viberoi] LocalStack bootstrap complete."

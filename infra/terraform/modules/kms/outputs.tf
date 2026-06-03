output "key_id" {
  description = "Raw key id — what the application code references via settings.kms_key_id."
  value       = aws_kms_key.this.key_id
}

output "key_arn" {
  description = "Full ARN — referenced by RDS, S3, SQS, Secrets Manager for SSE-KMS."
  value       = aws_kms_key.this.arn
}

output "alias_name" {
  description = "Alias name (with `alias/` prefix). Matches what the Python settings expect."
  value       = aws_kms_alias.this.name
}

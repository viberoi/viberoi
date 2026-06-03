output "org_data_bucket_id" {
  value       = aws_s3_bucket.org_data.id
  description = "Raw landing bucket name. Must equal RAW_BUCKET in viberoi_shared.s3 (currently `viberoi-org-data`; bumping requires a Python-side change)."
}

output "org_data_bucket_arn" {
  value       = aws_s3_bucket.org_data.arn
  description = "Used by the SQS queue's access policy to scope the source."
}

output "backups_bucket_id" {
  value = aws_s3_bucket.backups.id
}

output "backups_bucket_arn" {
  value = aws_s3_bucket.backups.arn
}

output "frontend_bucket_id" {
  value = aws_s3_bucket.frontend.id
}

output "frontend_bucket_arn" {
  value = aws_s3_bucket.frontend.arn
}

output "frontend_bucket_regional_domain_name" {
  value       = aws_s3_bucket.frontend.bucket_regional_domain_name
  description = "Used by CloudFront origin in 6E."
}

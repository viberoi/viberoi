output "state_bucket" {
  value       = aws_s3_bucket.tf_state.id
  description = "Name of the S3 state bucket — use in other modules' backend config."
}

output "lock_table" {
  value       = aws_dynamodb_table.tf_lock.name
  description = "Name of the DynamoDB lock table."
}

output "backend_config_snippet" {
  description = "Paste this into every other module's backend.tf."
  value       = <<-EOT
    terraform {
      backend "s3" {
        bucket         = "${aws_s3_bucket.tf_state.id}"
        key            = "envs/<env>/<module>.tfstate"
        region         = "${var.region}"
        dynamodb_table = "${aws_dynamodb_table.tf_lock.name}"
        encrypt        = true
      }
    }
  EOT
}

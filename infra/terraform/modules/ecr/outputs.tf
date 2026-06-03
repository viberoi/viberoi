output "repository_urls" {
  description = "Map from short name → repo URL. Used as the base for image refs in ECS task defs."
  value = {
    for k, r in aws_ecr_repository.this : k => r.repository_url
  }
}

output "repository_arns" {
  description = "Map from short name → ARN. Used in IAM policies for the deploy pipeline."
  value = {
    for k, r in aws_ecr_repository.this : k => r.arn
  }
}

output "repository_names" {
  description = "Map from short name → final repo name."
  value = {
    for k, r in aws_ecr_repository.this : k => r.name
  }
}

output "log_group_names" {
  description = "Map from short name → full log-group path. ECS task defs and Lambda functions reference these."
  value = {
    for k, g in aws_cloudwatch_log_group.this : k => g.name
  }
}

output "log_group_arns" {
  description = "Map for IAM policies that grant write permission."
  value = {
    for k, g in aws_cloudwatch_log_group.this : k => g.arn
  }
}

output "execution_role_arn" {
  description = "ARN to set on aws_ecs_task_definition.execution_role_arn or aws_lambda_function.role."
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "ARN to set on aws_ecs_task_definition.task_role_arn."
  value       = aws_iam_role.task.arn
}

output "execution_role_name" {
  value = aws_iam_role.execution.name
}

output "task_role_name" {
  value = aws_iam_role.task.name
}

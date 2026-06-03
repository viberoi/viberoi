output "service_name" {
  value       = aws_ecs_service.this.name
  description = "ECS service name — `aws ecs update-service --service <this>` for deploys."
}

output "task_definition_family" {
  value = aws_ecs_task_definition.this.family
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.this.arn
}

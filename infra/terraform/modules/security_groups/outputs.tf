output "alb_id" {
  description = "ALB SG - attached to the public load balancer."
  value       = aws_security_group.alb.id
}

output "services_id" {
  description = "Services SG - attached to every Fargate task."
  value       = aws_security_group.services.id
}

output "lambda_id" {
  description = "Lambda SG - attached to VPC-bound Lambdas."
  value       = aws_security_group.lambda.id
}

output "rds_id" {
  description = "RDS SG - attached to the Postgres instance."
  value       = aws_security_group.rds.id
}

output "redis_id" {
  description = "Redis SG - attached to the ElastiCache replication group."
  value       = aws_security_group.redis.id
}

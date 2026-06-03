output "function_name" {
  value = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN — passed to Cognito user pool `lambda_config`, API Gateway integrations, etc."
  value       = aws_lambda_function.this.arn
}

output "invoke_arn" {
  description = "API Gateway integration uses this form."
  value       = aws_lambda_function.this.invoke_arn
}

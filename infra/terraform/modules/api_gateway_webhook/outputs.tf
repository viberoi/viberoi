output "api_id" {
  value = aws_apigatewayv2_api.this.id
}

output "api_endpoint" {
  description = "Default endpoint - paste into GitHub/Jira/Linear webhook config until the custom domain is wired in 6E."
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "execution_arn" {
  description = "Used to scope Lambda permissions and (later) Cognito authorizers."
  value       = aws_apigatewayv2_api.this.execution_arn
}

output "user_pool_id" {
  description = "Used by `viberoi_shared.cognito.verify.jwks_url` and `iss` claim derivation."
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  description = "Used by Lambda trigger permissions and CloudWatch alarms."
  value       = aws_cognito_user_pool.this.arn
}

output "user_pool_endpoint" {
  description = "OIDC issuer URL - matches the `iss` claim in every Cognito token."
  value       = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}

output "spa_client_id" {
  description = "App client id - wired into the frontend's Cognito config."
  value       = aws_cognito_user_pool_client.spa.id
}

output "hosted_ui_domain" {
  description = "Full hosted-UI domain. Login URL = https://<domain>/login?client_id=..."
  value       = "${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.name}.amazoncognito.com"
}

output "hosted_ui_domain_prefix" {
  description = "Just the subdomain prefix - useful when wiring a custom domain in 6E."
  value       = aws_cognito_user_pool_domain.this.domain
}

data "aws_region" "current" {}

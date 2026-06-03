output "cloudfront_distribution" {
  description = "Underlying CloudFront domain — CNAME `<domain>` to this at Hostinger."
  value       = aws_cognito_user_pool_domain.custom.cloudfront_distribution_arn
}

output "domain" {
  description = "The custom domain string."
  value       = aws_cognito_user_pool_domain.custom.domain
}

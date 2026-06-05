output "distribution_id" {
  description = "Used to invalidate cache on deploy."
  value       = aws_cloudfront_distribution.this.id
}

output "distribution_domain_name" {
  description = "CloudFront-managed `.cloudfront.net` domain. CNAME `app.<your-domain>` to this at Hostinger."
  value       = aws_cloudfront_distribution.this.domain_name
}

output "distribution_hosted_zone_id" {
  description = "Z2FDTNDATAQYW2 - same for every CloudFront distribution. For an A-alias if you ever migrate DNS to Route 53."
  value       = aws_cloudfront_distribution.this.hosted_zone_id
}

output "distribution_arn" {
  value = aws_cloudfront_distribution.this.arn
}

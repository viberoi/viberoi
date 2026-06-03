output "certificate_arn" {
  description = "Cert ARN. Pass to ALB listener / CloudFront / Cognito custom domain."
  value       = aws_acm_certificate.this.arn
}

output "domain_validation_options" {
  description = "DNS validation records. For each domain, add a CNAME at Hostinger: name → value. Once added, AWS validates within ~30 min."
  value = {
    for opt in aws_acm_certificate.this.domain_validation_options :
    opt.domain_name => {
      record_name  = opt.resource_record_name
      record_value = opt.resource_record_value
      record_type  = opt.resource_record_type
    }
  }
}

output "certificate_status" {
  description = "PENDING_VALIDATION until you add the CNAMEs to Hostinger. ISSUED once validated."
  value       = aws_acm_certificate.this.status
}

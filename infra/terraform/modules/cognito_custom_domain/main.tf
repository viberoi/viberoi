# Cognito hosted-UI custom domain.
#
# Requirements (Cognito hard rules):
#   - ACM cert in us-east-1 covering `domain`.
#   - Cert must be ISSUED at apply time (not just requested).
#   - The parent domain (apex) must have an A record at Cognito's parent
#     domain check. For subdomains like `auth.viberoi.io`, AWS verifies
#     `viberoi.io` has SOA / NS records — which it always will if you
#     own the domain.
#
# After apply: CNAME `domain` → `cloudfront_distribution` (output below)
# at Hostinger.

resource "aws_cognito_user_pool_domain" "custom" {
  domain          = var.domain
  user_pool_id    = var.user_pool_id
  certificate_arn = var.certificate_arn
}

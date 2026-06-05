# ACM certificate with DNS validation.
#
# DNS lives at Hostinger (user-managed). We can't create the validation
# records ourselves, so we:
#   1. Request the cert in PENDING_VALIDATION state.
#   2. Emit `validation_records` as an output - a map keyed by domain →
#      `{name, value}`. User pastes these into Hostinger as CNAMEs.
#   3. Skip `aws_acm_certificate_validation` - that resource blocks on
#      `terraform apply` until validation completes, which requires the
#      user action above. Validation completes asynchronously; usually
#      within 30 minutes of the CNAME being added.
#
# ALB can attach an unvalidated cert (HTTPS just won't serve until it's
# validated). CloudFront REQUIRES a validated cert at create time -
# either wait for validation before applying CloudFront, or split into
# two terraform runs.

locals {
  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "acm_cert"
    },
    var.tags,
  )
}

resource "aws_acm_certificate" "this" {
  domain_name               = var.domain
  subject_alternative_names = var.subject_alternative_names
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, { Name = "${var.project}-${var.env}-cert" })
}

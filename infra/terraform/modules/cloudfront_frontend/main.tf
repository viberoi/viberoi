# CloudFront distribution fronting the frontend S3 bucket.
#
# - Origin Access Control (OAC) — newer than OAI. Distribution signs
#   the S3 request; bucket policy allows reads only from this dist.
# - SPA fallback: 403/404 → /index.html with 200. Vite + React Router
#   handles the rest client-side.
# - HTTPS only — Redirect HTTP to HTTPS via viewer_protocol_policy.
# - Compress responses. Default cache + origin request policies
#   (we don't need fine-grained tuning yet).
#
# Custom domain requires ACM cert in us-east-1 — CloudFront's hard
# requirement. We're already in us-east-1 so it's the same provider.

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "cloudfront_frontend"
    },
    var.tags,
  )

  use_custom_domain = length(var.aliases) > 0 && var.certificate_arn != null
}

# ── Origin Access Control ─────────────────────────────────────────────────
resource "aws_cloudfront_origin_access_control" "this" {
  name                              = "${local.prefix}-frontend-oac"
  description                       = "OAC for the env's frontend bucket."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ── Distribution ──────────────────────────────────────────────────────────
resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100" # US/EU edges only — cheapest
  comment             = "${local.prefix} — frontend"
  aliases             = var.aliases

  origin {
    domain_name              = var.frontend_bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.this.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # Managed cache policy: CachingOptimized.
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  # SPA fallback — Vite/React Router owns the URL space client-side.
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  viewer_certificate {
    cloudfront_default_certificate = !local.use_custom_domain
    acm_certificate_arn            = local.use_custom_domain ? var.certificate_arn : null
    ssl_support_method             = local.use_custom_domain ? "sni-only" : null
    minimum_protocol_version       = local.use_custom_domain ? "TLSv1.2_2021" : null
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = merge(local.common_tags, { Name = "${local.prefix}-frontend-cdn" })
}

# ── Bucket policy — allow this distribution only ──────────────────────────
data "aws_iam_policy_document" "bucket" {
  statement {
    sid    = "AllowCloudFrontServicePrincipalRead"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions   = ["s3:GetObject"]
    resources = ["${var.frontend_bucket_arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.this.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = var.frontend_bucket_id
  policy = data.aws_iam_policy_document.bucket.json
}

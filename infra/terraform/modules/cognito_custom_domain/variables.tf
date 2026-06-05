variable "user_pool_id" {
  type        = string
  description = "Cognito user pool to attach the custom domain to. From modules/cognito.user_pool_id."
}

variable "domain" {
  type        = string
  description = "Full FQDN - e.g. auth.viberoi.io. Must NOT have a CNAME at the apex."
}

variable "certificate_arn" {
  type        = string
  description = "ACM cert in us-east-1 covering `domain`. Must be ISSUED at the time of apply (Cognito requires validated cert)."
}

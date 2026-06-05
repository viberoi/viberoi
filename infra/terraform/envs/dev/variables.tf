variable "project" {
  type        = string
  default     = "viberoi"
  description = "Stable prefix on every resource."
}

variable "env" {
  type        = string
  default     = "dev"
  description = "Environment short name. Reflected in every resource name."
}

variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region. Cognito + CloudFront ACM cert live here too."
}

variable "vpc_cidr" {
  type        = string
  default     = "10.20.0.0/16"
  description = "Top-level VPC CIDR - sliced into /20 per subnet."
}

variable "az_count" {
  type        = number
  default     = 2
  description = "Number of AZs. 2 keeps dev cheap; bump to 3 for staging/prod."
}

variable "single_nat" {
  type        = bool
  default     = true
  description = "Dev: one NAT to save ~$32/AZ. Set false in prod."
}

variable "domain" {
  type        = string
  default     = ""
  description = "Apex domain - e.g. viberoi.io. Empty disables 6E (ACM/ALB-cert/CloudFront-custom-domain/Cognito-custom-domain stay blank). When set, terraform creates an ACM cert covering app.<domain>, api.<domain>, auth.<domain>, webhooks.<domain> - you then add the validation CNAMEs at Hostinger."
}

variable "enable_cognito_custom_domain" {
  type        = bool
  default     = false
  description = "Phase 3 toggle - flip to true ONLY after the ACM cert is ISSUED (cognito custom domains refuse pending certs). See envs/dev/README."
}

variable "enable_cloudfront_custom_domain" {
  type        = bool
  default     = false
  description = "Phase 3 toggle - same rule as cognito. CloudFront refuses an unvalidated cert at create time."
}

# ── Cognito federated IdPs (optional) ──────────────────────────────────────
# Leave empty and Cognito stays native-only (email + OTP). Fill in via
# `TF_VAR_google_client_id` etc when you have IdP credentials.
variable "google_client_id" {
  type    = string
  default = ""
}

variable "google_client_secret" {
  type      = string
  sensitive = true
  default   = ""
}

variable "github_oidc_client_id" {
  type    = string
  default = ""
}

variable "github_oidc_client_secret" {
  type      = string
  sensitive = true
  default   = ""
}


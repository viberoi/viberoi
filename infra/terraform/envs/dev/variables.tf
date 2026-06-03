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
  description = "Top-level VPC CIDR — sliced into /20 per subnet."
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
  description = "Public domain for ALB + CloudFront. Empty until wired in 6E."
}

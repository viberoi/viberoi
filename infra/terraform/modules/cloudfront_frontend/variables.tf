variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "frontend_bucket_id" {
  type        = string
  description = "S3 bucket id for the Vite build. From modules/s3.frontend_bucket_id."
}

variable "frontend_bucket_regional_domain_name" {
  type        = string
  description = "From modules/s3.frontend_bucket_regional_domain_name."
}

variable "frontend_bucket_arn" {
  type        = string
  description = "Used in the bucket policy so CloudFront's OAC has read access."
}

variable "aliases" {
  type        = list(string)
  description = "Custom domain CNAMEs - e.g. ['app.viberoi.io']. Empty list = CloudFront-only domain."
  default     = []
}

variable "certificate_arn" {
  type        = string
  description = "ACM cert ARN (us-east-1 - CloudFront requirement). Null = use CloudFront default cert (only valid when aliases is empty)."
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}

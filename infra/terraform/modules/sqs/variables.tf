variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "kms_key_arn" {
  type        = string
  description = "KMS CMK for SQS server-side encryption."
}

variable "raw_landing_bucket_arn" {
  type        = string
  description = "S3 bucket whose events publish to session_ingest. Bucket policy scopes the source so other buckets can't publish."
}

variable "visibility_timeout_seconds" {
  type    = number
  default = 30
}

variable "message_retention_seconds" {
  type        = number
  default     = 1209600 # 14 days
  description = "AWS max."
}

variable "max_receive_count" {
  type        = number
  default     = 3
  description = "DLQ trigger threshold."
}

variable "tags" {
  type    = map(string)
  default = {}
}

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
  description = "KMS CMK for SSE-KMS. Output of modules/kms."
}

variable "account_id" {
  type        = string
  description = "Account id is appended to bucket names for global uniqueness."

  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be a 12-digit AWS account number."
  }
}

variable "raw_landing_retention_days" {
  type        = number
  description = "Lifecycle: how long to keep raw session JSONL. Worker has long since upserted to DB by then."
  default     = 365
}

variable "tags" {
  type    = map(string)
  default = {}
}

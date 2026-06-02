variable "project" {
  type        = string
  default     = "viberoi"
  description = "Project name — used to prefix all resources."
}

variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region for the state bucket and lock table."
}

variable "account_id" {
  type        = string
  description = "AWS account ID. Appended to the bucket name for global uniqueness."

  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be a 12-digit AWS account number."
  }
}

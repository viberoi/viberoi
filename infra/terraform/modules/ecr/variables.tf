variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "repo_names" {
  type        = list(string)
  description = "Short names - one repo per. Final repo name = $${project}-$${env}-<name>."
}

variable "kms_key_arn" {
  type        = string
  description = "KMS CMK for image layer encryption."
}

variable "expire_untagged_after_days" {
  type        = number
  default     = 14
  description = "Untagged manifests removed after N days. Old GitHub-Actions pushes that didn't get promoted."
}

variable "keep_tagged_count" {
  type        = number
  default     = 30
  description = "Keep the N most-recent tagged images per repo."
}

variable "tags" {
  type    = map(string)
  default = {}
}

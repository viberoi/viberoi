variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "alias" {
  type        = string
  description = "Key alias short name. Final form: alias/<alias>. Must match settings.kms_key_id."
  default     = "viberoi-pii"
}

variable "deletion_window_days" {
  type        = number
  description = "Wait window before key is actually deleted. Min 7, max 30."
  default     = 30
}

variable "enable_key_rotation" {
  type        = bool
  description = "AWS automatically rotates the CMK material annually. Reads continue to work across versions transparently."
  default     = true
}

variable "additional_iam_arns" {
  type        = list(string)
  description = "IAM principals (role/user ARNs) that get encrypt/decrypt permissions. Service task roles go here once they exist (6D)."
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}

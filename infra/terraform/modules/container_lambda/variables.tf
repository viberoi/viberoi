variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "name" {
  type        = string
  description = "Lambda short name. Final = $${project}-$${env}-<name>."
}

variable "image_uri" {
  type        = string
  description = "Full ECR image URI including tag."
}

variable "role_arn" {
  type        = string
  description = "Execution role ARN. From modules/iam_task_role (assume_role_service=lambda.amazonaws.com)."
}

variable "vpc_subnet_ids" {
  type        = list(string)
  default     = []
  description = "Empty = no VPC attach. Set to private_subnet_ids when the Lambda needs DB/Redis access."
}

variable "vpc_security_group_ids" {
  type    = list(string)
  default = []
}

variable "env_vars" {
  type    = map(string)
  default = {}
}

variable "timeout_seconds" {
  type    = number
  default = 30
}

variable "memory_mb" {
  type    = number
  default = 512
}

variable "log_group_name" {
  type        = string
  description = "From modules/log_groups. The function reads /aws/lambda/<name> if not set; we use the explicit shared log group for consistency."
  default     = null
}

variable "log_retention_days" {
  type        = number
  description = "Used only when this module owns the log group (when log_group_name is null)."
  default     = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}

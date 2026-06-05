variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "service_names" {
  type        = list(string)
  description = "Short names - one log group per. Final = /viberoi/<env>/<kind>/<name>."
}

variable "log_kind" {
  type        = string
  description = "ecs | lambda - slotted into the log-group path so the console tree is clean."

  validation {
    condition     = contains(["ecs", "lambda"], var.log_kind)
    error_message = "log_kind must be ecs or lambda."
  }
}

variable "retention_days" {
  type    = number
  default = 30
}

variable "kms_key_arn" {
  type        = string
  description = "CloudWatch logs require a key whose policy allows logs.amazonaws.com - see README."
}

variable "tags" {
  type    = map(string)
  default = {}
}

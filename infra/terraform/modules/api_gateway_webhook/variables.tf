variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "lambda_function_name" {
  type        = string
  description = "Webhook receiver Lambda function name."
}

variable "lambda_invoke_arn" {
  type        = string
  description = "Webhook receiver Lambda invoke ARN."
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}

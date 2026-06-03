variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "service_name" {
  type        = string
  description = "Service short name: ingest | worker | integration | api | notification."
}

variable "assume_role_service" {
  type        = string
  description = "Service principal. ECS = `ecs-tasks.amazonaws.com`, Lambda = `lambda.amazonaws.com`."
  default     = "ecs-tasks.amazonaws.com"
}

# ── Scoped permissions ─────────────────────────────────────────────────────
variable "kms_key_arn" {
  type        = string
  description = "KMS CMK the service needs to encrypt/decrypt. Required."
}

variable "secret_arns" {
  type        = list(string)
  description = "Secrets Manager ARNs this service reads (GetSecretValue + Describe)."
  default     = []
}

variable "sqs_send_arns" {
  type        = list(string)
  description = "Queues this service publishes to (sqs:SendMessage)."
  default     = []
}

variable "sqs_receive_arns" {
  type        = list(string)
  description = "Queues this service consumes (sqs:ReceiveMessage / DeleteMessage / GetQueueAttributes / GetQueueUrl / ChangeMessageVisibility)."
  default     = []
}

variable "s3_read_arns" {
  type        = list(string)
  description = "Bucket ARNs the service reads from. Object-level access is granted automatically."
  default     = []
}

variable "s3_write_arns" {
  type        = list(string)
  description = "Bucket ARNs the service writes to. Object-level access is granted automatically."
  default     = []
}

variable "cognito_user_pool_arn" {
  type        = string
  description = "If set, the service gets cognito-idp:AdminUpdateUserAttributes. Used by the PostConfirmation Lambda."
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}

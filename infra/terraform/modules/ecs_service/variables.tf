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
  description = "Short name: ingest | worker | integration | api | notification."
}

variable "cluster_id" {
  type        = string
  description = "ECS cluster ARN. From modules/ecs_cluster.cluster_id."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnets the task runs in. From modules/vpc.private_subnet_ids."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Typically [modules/security_groups.services_id]."
}

variable "image_uri" {
  type        = string
  description = "Full image URI including tag. e.g. <repo_url>:<sha>. GitHub Actions updates tag via `aws ecs update-service` in 6F."
}

variable "execution_role_arn" {
  type        = string
  description = "From modules/iam_task_role.execution_role_arn."
}

variable "task_role_arn" {
  type        = string
  description = "From modules/iam_task_role.task_role_arn."
}

variable "log_group_name" {
  type        = string
  description = "From modules/log_groups.log_group_names[service_name]."
}

variable "container_port" {
  type        = number
  description = "Port the container listens on. 0 for pure consumers (worker, notification) - no port published."
  default     = 0
}

variable "cpu" {
  type        = number
  default     = 256
  description = "Fargate CPU units. 256 = 0.25 vCPU. Quarter-vCPU pairs with 512 MB memory minimum."
}

variable "memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  type        = number
  default     = 0
  description = "Set to 0 by default so first apply doesn't try to pull an image that hasn't been pushed yet. Bump to >=1 after the deploy pipeline pushes."
}

variable "env_vars" {
  type        = map(string)
  default     = {}
  description = "Plaintext env vars. Secrets go via `secrets`, not here."
}

variable "secrets" {
  type        = map(string)
  default     = {}
  description = "Map from env-var name → Secrets Manager ARN. ECS fetches at task start. Execution role must have GetSecretValue on each ARN."
}

variable "load_balancer" {
  type = object({
    target_group_arn = string
    container_port   = number
  })
  default     = null
  description = "ALB attachment. Null for non-HTTP services (worker, notification)."
}

variable "command" {
  type        = list(string)
  default     = null
  description = "Override the container's CMD."
}

variable "tags" {
  type    = map(string)
  default = {}
}

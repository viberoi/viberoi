variable "project" {
  type        = string
  description = "Project name - prefixed on every resource."
  default     = "viberoi"
}

variable "env" {
  type        = string
  description = "Environment name - dev | staging | prod."

  validation {
    condition     = contains(["dev", "staging", "prod"], var.env)
    error_message = "env must be one of: dev, staging, prod."
  }
}

variable "cidr_block" {
  type        = string
  description = "VPC CIDR. /16 gives plenty of room; we slice /20 per subnet."
  default     = "10.20.0.0/16"
}

variable "az_count" {
  type        = number
  description = "Number of AZs to use. 2 for dev (NAT cost), 3 for prod (durability)."
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be 2 or 3."
  }
}

variable "single_nat" {
  type        = bool
  description = "Use a single NAT gateway across all private subnets. Saves ~$32/AZ in dev. Set false for prod (HA)."
  default     = true
}

variable "enable_vpc_endpoints" {
  type        = bool
  description = "Create gateway endpoints for S3/DynamoDB + interface endpoints for ECR, Secrets Manager, SQS, Logs. Cuts NAT traffic + cost in prod. Off in dev because the interface endpoints cost ~$7/mo each."
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Tags merged into every resource."
  default     = {}
}

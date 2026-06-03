variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "vpc_id" {
  type        = string
  description = "VPC the ALB lives in. From modules/vpc.vpc_id."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Public subnets the ALB attaches to. From modules/vpc.public_subnet_ids."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Typically [modules/security_groups.alb_id]."
}

variable "certificate_arn" {
  type        = string
  description = "ACM cert ARN for the HTTPS listener. From modules/acm_cert.certificate_arn."
}

# ── Target group definitions ──────────────────────────────────────────────
# One map entry per HTTP backend service. Each entry creates a target
# group + a listener rule.
variable "services" {
  type = map(object({
    container_port = number
    health_path    = string
    # Path patterns the rule matches. The DEFAULT target group is named
    # "api" by convention — everything that doesn't match another rule
    # falls through to api.
    path_patterns = list(string)
    priority      = number
  }))

  description = "Map service_name → routing config."

  default = {
    ingest = {
      container_port = 8001
      health_path    = "/healthz"
      path_patterns  = ["/ingest/*", "/agent/*"]
      priority       = 100
    }
    integration = {
      container_port = 8002
      health_path    = "/healthz"
      path_patterns  = ["/integrations/*"]
      priority       = 200
    }
    api = {
      container_port = 8003
      health_path    = "/healthz"
      path_patterns  = ["*"]
      priority       = 1000
    }
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}

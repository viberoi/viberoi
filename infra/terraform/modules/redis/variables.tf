variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "data_subnet_ids" {
  type        = list(string)
  description = "Subnets the cluster lives in. From modules/vpc data_subnet_ids."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Typically just [modules/security_groups.redis_id]."
}

variable "kms_key_arn" {
  type        = string
  description = "At-rest encryption key. Output of modules/kms."
}

variable "node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "engine_version" {
  type    = string
  default = "7.1"
}

variable "num_cache_clusters" {
  type        = number
  default     = 1
  description = "1 = single-node (dev). 2+ = primary + N replicas."
}

variable "tags" {
  type    = map(string)
  default = {}
}

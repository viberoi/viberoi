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
  description = "Subnets the DB lives in. From modules/vpc data_subnet_ids."
}

variable "security_group_ids" {
  type        = list(string)
  description = "SGs attached to the instance. Typically just modules/security_groups.rds_id."
}

variable "kms_key_arn" {
  type        = string
  description = "Storage encryption key. Output of modules/kms."
}

variable "master_password" {
  type        = string
  description = "Master user password. From modules/secrets random_password.rds_master.result."
  sensitive   = true
}

variable "instance_class" {
  type        = string
  default     = "db.t4g.micro"
  description = "Cheapest viable option for dev; bump in prod."
}

variable "allocated_storage_gb" {
  type    = number
  default = 20
}

variable "max_allocated_storage_gb" {
  type        = number
  default     = 100
  description = "Auto-scaling cap."
}

variable "engine_version" {
  type    = string
  default = "16.3"
}

variable "multi_az" {
  type        = bool
  default     = false
  description = "Dev: single AZ saves ~50%. Flip to true in staging+."
}

variable "backup_retention_days" {
  type    = number
  default = 7
}

variable "deletion_protection" {
  type    = bool
  default = true
}

variable "skip_final_snapshot" {
  type        = bool
  default     = false
  description = "Set true in dev only if you're certain you don't need the snapshot."
}

variable "tags" {
  type    = map(string)
  default = {}
}

# Dev environment composition.
#
# Slice 6A: vpc + security_groups
# Slice 6B: kms + secrets + s3 + sqs + rds + redis (this commit)
# Slice 6C: cognito + user pool + IdP + lambda triggers
# Slice 6D: ecr + ecs cluster + ecs services
# Slice 6E: alb + route53 + acm + cloudfront + api gateway
# Slice 6F: cloudwatch alarms + GitHub Actions deploy

provider "aws" {
  region = var.region

  default_tags {
    tags = local.common_tags
  }
}

data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project}-${var.env}"

  common_tags = {
    Project   = var.project
    Env       = var.env
    ManagedBy = "terraform"
    Stack     = "envs/dev"
  }
}

# ── Networking ─────────────────────────────────────────────────────────────
module "vpc" {
  source = "../../modules/vpc"

  project              = var.project
  env                  = var.env
  cidr_block           = var.vpc_cidr
  az_count             = var.az_count
  single_nat           = var.single_nat
  enable_vpc_endpoints = false # dev: skip the ~$7/mo per interface endpoint
  tags                 = local.common_tags
}

module "security_groups" {
  source = "../../modules/security_groups"

  project = var.project
  env     = var.env
  vpc_id  = module.vpc.vpc_id
  tags    = local.common_tags
}

# ── Crypto + secrets ───────────────────────────────────────────────────────
module "kms" {
  source = "../../modules/kms"

  project = var.project
  env     = var.env
  # additional_iam_arns is wired in 6D once task roles exist; for now the
  # root account is the only principal that can use the key.
  tags = local.common_tags
}

module "secrets" {
  source = "../../modules/secrets"

  project     = var.project
  env         = var.env
  kms_key_arn = module.kms.key_arn
  tags        = local.common_tags
}

# ── Storage + queues ───────────────────────────────────────────────────────
module "s3" {
  source = "../../modules/s3"

  project     = var.project
  env         = var.env
  kms_key_arn = module.kms.key_arn
  account_id  = data.aws_caller_identity.current.account_id
  tags        = local.common_tags
}

module "sqs" {
  source = "../../modules/sqs"

  project                = var.project
  env                    = var.env
  kms_key_arn            = module.kms.key_arn
  raw_landing_bucket_arn = module.s3.org_data_bucket_arn
  tags                   = local.common_tags
}

# S3 → SQS event notification. Wired here (not inside modules/s3) so the
# direction of the dependency is explicit and the queue policy is in
# place before the notification fires.
resource "aws_s3_bucket_notification" "raw_landing_to_sqs" {
  bucket = module.s3.org_data_bucket_id

  queue {
    queue_arn = module.sqs.queue_arns["session_ingest"]
    events    = ["s3:ObjectCreated:*"]
  }

  depends_on = [module.sqs]
}

# ── Databases ──────────────────────────────────────────────────────────────
module "rds" {
  source = "../../modules/rds"

  project            = var.project
  env                = var.env
  data_subnet_ids    = module.vpc.data_subnet_ids
  security_group_ids = [module.security_groups.rds_id]
  kms_key_arn        = module.kms.key_arn
  master_password    = module.secrets.rds_master_password

  # Dev defaults — match module defaults explicitly so changes here are visible.
  instance_class        = "db.t4g.micro"
  multi_az              = false
  backup_retention_days = 7
  deletion_protection   = true
  tags                  = local.common_tags
}

module "redis" {
  source = "../../modules/redis"

  project            = var.project
  env                = var.env
  data_subnet_ids    = module.vpc.data_subnet_ids
  security_group_ids = [module.security_groups.redis_id]
  kms_key_arn        = module.kms.key_arn

  node_type          = "cache.t4g.micro"
  num_cache_clusters = 1
  tags               = local.common_tags
}

# ── Outputs ────────────────────────────────────────────────────────────────
# Re-export the things later modules + the GitHub Actions deploy pipeline
# need. Anything that's *not* secret can live here.
output "account_id" {
  description = "AWS account id this env is provisioned in."
  value       = data.aws_caller_identity.current.account_id
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "data_subnet_ids" {
  value = module.vpc.data_subnet_ids
}

output "sg_alb" {
  value = module.security_groups.alb_id
}

output "sg_services" {
  value = module.security_groups.services_id
}

output "sg_lambda" {
  value = module.security_groups.lambda_id
}

output "sg_rds" {
  value = module.security_groups.rds_id
}

output "sg_redis" {
  value = module.security_groups.redis_id
}

# ── 6B outputs ─────────────────────────────────────────────────────────────
output "kms_key_arn" {
  value = module.kms.key_arn
}

output "kms_alias_name" {
  value = module.kms.alias_name
}

output "rds_endpoint" {
  description = "host:port for DATABASE_URL."
  value       = module.rds.endpoint
}

output "rds_master_username" {
  value = module.rds.master_username
}

output "rds_db_name" {
  value = module.rds.db_name
}

output "redis_primary_endpoint" {
  value = module.redis.primary_endpoint_address
}

output "redis_port" {
  value = module.redis.port
}

output "org_data_bucket" {
  value = module.s3.org_data_bucket_id
}

output "frontend_bucket" {
  value = module.s3.frontend_bucket_id
}

output "frontend_bucket_regional_domain_name" {
  value = module.s3.frontend_bucket_regional_domain_name
}

output "sqs_queue_arns" {
  description = "Map of short-name → queue ARN. Task role IAM policies use these in 6D."
  value       = module.sqs.queue_arns
}

output "sqs_dlq_arns" {
  description = "Map of short-name → DLQ ARN. CloudWatch alarms attach in 6F."
  value       = module.sqs.dlq_arns
}

output "secret_arns" {
  description = "All Secrets Manager ARNs — task roles get decrypt permission on these in 6D."
  value       = module.secrets.all_secret_arns
}

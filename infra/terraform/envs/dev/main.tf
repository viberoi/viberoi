# Dev environment composition.
#
# Adds modules in subsequent sub-batches (6B–6F):
#   - 6B: rds, redis, s3, sqs, kms, secrets_manager
#   - 6C: cognito (user pool + app client + IdP + lambda triggers)
#   - 6D: ecr_repos, ecs_cluster, ecs_service (one per backend service)
#   - 6E: alb, route53, acm, cloudfront, api_gateway
#   - 6F: cloudwatch_alarms, github_actions_deploy

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

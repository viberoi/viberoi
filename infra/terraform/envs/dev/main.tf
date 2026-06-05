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

  # Dev defaults - match module defaults explicitly so changes here are visible.
  # backup_retention=1 to stay inside the AWS free tier (account limit;
  # bumps to 7+ break with FreeTierRestrictionError until the plan upgrades).
  instance_class        = "db.t4g.micro"
  multi_az              = false
  backup_retention_days = 1
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

# ── Cognito ────────────────────────────────────────────────────────────────
# Lambda trigger ARNs flow from the Lambda module declarations below -
# Terraform handles the dependency ordering.
module "cognito" {
  source = "../../modules/cognito"

  project = var.project
  env     = var.env

  # Local-dev callbacks always live here. The deployed-app callback gets
  # appended when `var.domain` is set - Cognito accepts multiple, so
  # both local and prod work from the same pool with one apply.
  callback_urls = concat(
    [
      "http://localhost:5173/auth/callback",
      "http://127.0.0.1:5173/auth/callback",
    ],
    var.domain != "" ? ["https://app.${var.domain}/auth/callback"] : [],
  )
  logout_urls = concat(
    [
      "http://localhost:5173/",
      "http://127.0.0.1:5173/",
    ],
    var.domain != "" ? ["https://app.${var.domain}/"] : [],
  )

  # Federated IdPs - empty defaults → no IdPs created. Set
  # TF_VAR_google_client_id etc to enable.
  google_client_id          = var.google_client_id
  google_client_secret      = var.google_client_secret
  github_oidc_client_id     = var.github_oidc_client_id
  github_oidc_client_secret = var.github_oidc_client_secret

  # Lambda trigger wiring - TWO-PHASE APPLY (see README "Phase 2 - wire
  # Cognito triggers"). Phase 1 leaves these as literal null because
  # Cognito's `lambda_config` would create a graph cycle with the Lambda
  # env vars (which themselves depend on the user pool id).
  #
  # Phase 2 runbook: replace the three lines below with the three commented
  # references and `terraform apply` again. The Lambda functions will
  # exist by then, the dependency graph is acyclic, and `lambda_config`
  # is emitted on the pool.
  #
  # lambda_pre_signup_arn           = module.lambda_cognito_presignup.function_arn
  # lambda_post_confirmation_arn    = module.lambda_cognito_postconfirm.function_arn
  # lambda_pre_token_generation_arn = module.lambda_cognito_pre_token_gen.function_arn
  lambda_pre_signup_arn           = null
  lambda_post_confirmation_arn    = null
  lambda_pre_token_generation_arn = null

  deletion_protection = "INACTIVE" # dev - easier teardown
  tags                = local.common_tags
}

# ── ECR + ECS cluster + log groups ─────────────────────────────────────────
module "ecr" {
  source = "../../modules/ecr"

  project = var.project
  env     = var.env
  repo_names = [
    "ingest",
    "worker",
    "integration",
    "api",
    "notification",
    "webhook-receiver",
    "cognito-presignup",
    "cognito-postconfirm",
    "cognito-pre-token-gen",
  ]
  kms_key_arn = module.kms.key_arn
  tags        = local.common_tags
}

module "ecs_cluster" {
  source = "../../modules/ecs_cluster"

  project = var.project
  env     = var.env
  tags    = local.common_tags
}

module "log_groups_ecs" {
  source = "../../modules/log_groups"

  project        = var.project
  env            = var.env
  service_names  = ["ingest", "worker", "integration", "api", "notification"]
  log_kind       = "ecs"
  retention_days = 30
  kms_key_arn    = module.kms.key_arn
  tags           = local.common_tags
}

module "log_groups_lambda" {
  source = "../../modules/log_groups"

  project = var.project
  env     = var.env
  service_names = [
    "webhook-receiver",
    "cognito-presignup",
    "cognito-postconfirm",
    "cognito-pre-token-gen",
  ]
  log_kind       = "lambda"
  retention_days = 30
  kms_key_arn    = module.kms.key_arn
  tags           = local.common_tags
}

# ── IAM task roles - one per service / Lambda ──────────────────────────────
locals {
  # Image refs use the `:bootstrap` tag - a placeholder GitHub Actions
  # replaces with `:<commit-sha>` on first deploy. Until that push, the
  # tasks stay at desired_count=0 so missing-image isn't a runtime
  # failure.
  ecs_services = ["ingest", "worker", "integration", "api", "notification"]
  lambdas = [
    "webhook-receiver",
    "cognito-presignup",
    "cognito-postconfirm",
    "cognito-pre-token-gen",
  ]

  # Common runtime env vars every backend service needs.
  common_runtime_env = {
    VIBEROI_ENV                   = var.env
    VIBEROI_AWS_REGION            = var.region
    VIBEROI_KMS_KEY_ID            = module.kms.alias_name
    VIBEROI_REDIS_URL             = "rediss://${module.redis.primary_endpoint_address}:${module.redis.port}/0"
    VIBEROI_COGNITO_USER_POOL_ID  = module.cognito.user_pool_id
    VIBEROI_COGNITO_REGION        = var.region
    VIBEROI_COGNITO_APP_CLIENT_ID = module.cognito.spa_client_id
    # DB URL assembled at app startup from RDS host + master password
    # secret. See viberoi_shared.config.settings.model_post_init.
    VIBEROI_DATABASE_HOST = element(split(":", module.rds.endpoint), 0)
    VIBEROI_DATABASE_USER = "postgres"
  }

  # Secret refs every service needs - name → Secrets Manager ARN.
  # Application code reads via viberoi_shared.secrets.get(name) but
  # ECS can also inject as env vars; for now we use env-var injection
  # to keep app code unchanged.
  common_runtime_secrets = {
    VIBEROI_RDS_MASTER_PASSWORD = module.secrets.rds_master_password_arn
    VIBEROI_LOOKUP_PEPPER       = module.secrets.lookup_pepper_arn
  }
}

# Ingest - pushes to S3 raw landing.
module "iam_ingest" {
  source = "../../modules/iam_task_role"

  project       = var.project
  env           = var.env
  service_name  = "ingest"
  kms_key_arn   = module.kms.key_arn
  secret_arns   = [module.secrets.rds_master_password_arn, module.secrets.lookup_pepper_arn]
  s3_write_arns = [module.s3.org_data_bucket_arn]
  tags          = local.common_tags
}

# Worker - consumes session_ingest + webhook_events; reads raw S3.
module "iam_worker" {
  source = "../../modules/iam_task_role"

  project      = var.project
  env          = var.env
  service_name = "worker"
  kms_key_arn  = module.kms.key_arn
  secret_arns  = [module.secrets.rds_master_password_arn, module.secrets.lookup_pepper_arn]
  s3_read_arns = [module.s3.org_data_bucket_arn]
  sqs_receive_arns = [
    module.sqs.queue_arns["session_ingest"],
    module.sqs.queue_arns["webhook_events"],
  ]
  sqs_send_arns = [module.sqs.queue_arns["notification_jobs"]]
  tags          = local.common_tags
}

# Integration - outbound HTTPS to providers; consumes backfill_jobs;
# publishes to backfill_jobs (re-enqueue) + notification_jobs.
module "iam_integration" {
  source = "../../modules/iam_task_role"

  project      = var.project
  env          = var.env
  service_name = "integration"
  kms_key_arn  = module.kms.key_arn
  secret_arns = [
    module.secrets.rds_master_password_arn,
    module.secrets.lookup_pepper_arn,
    module.secrets.github_app_private_key_arn,
    module.secrets.jira_client_secret_arn,
    module.secrets.linear_client_secret_arn,
  ]
  sqs_send_arns = [
    module.sqs.queue_arns["backfill_jobs"],
    module.sqs.queue_arns["notification_jobs"],
  ]
  sqs_receive_arns = [module.sqs.queue_arns["backfill_jobs"]]
  tags             = local.common_tags
}

# API - read-only dashboard backend.
module "iam_api" {
  source = "../../modules/iam_task_role"

  project      = var.project
  env          = var.env
  service_name = "api"
  kms_key_arn  = module.kms.key_arn
  secret_arns  = [module.secrets.rds_master_password_arn, module.secrets.lookup_pepper_arn]
  tags         = local.common_tags
}

# Notification - consumes notification_jobs, delivers to Slack/Teams.
module "iam_notification" {
  source = "../../modules/iam_task_role"

  project          = var.project
  env              = var.env
  service_name     = "notification"
  kms_key_arn      = module.kms.key_arn
  secret_arns      = [module.secrets.rds_master_password_arn, module.secrets.lookup_pepper_arn]
  sqs_receive_arns = [module.sqs.queue_arns["notification_jobs"]]
  tags             = local.common_tags
}

# ── ECS services - desired_count=0 until first image push ─────────────────
module "ecs_ingest" {
  source = "../../modules/ecs_service"

  project            = var.project
  env                = var.env
  service_name       = "ingest"
  cluster_id         = module.ecs_cluster.cluster_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.services_id]
  image_uri          = "${module.ecr.repository_urls["ingest"]}:bootstrap"
  execution_role_arn = module.iam_ingest.execution_role_arn
  task_role_arn      = module.iam_ingest.task_role_arn
  log_group_name     = module.log_groups_ecs.log_group_names["ingest"]
  container_port     = 8001
  env_vars           = local.common_runtime_env
  secrets            = local.common_runtime_secrets

  # ALB attachment - only when the ALB exists (domain set).
  load_balancer = var.domain != "" ? {
    target_group_arn = module.alb[0].target_group_arns["ingest"]
    container_port   = 8001
  } : null

  tags = local.common_tags
}

module "ecs_worker" {
  source = "../../modules/ecs_service"

  project            = var.project
  env                = var.env
  service_name       = "worker"
  cluster_id         = module.ecs_cluster.cluster_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.services_id]
  image_uri          = "${module.ecr.repository_urls["worker"]}:bootstrap"
  execution_role_arn = module.iam_worker.execution_role_arn
  task_role_arn      = module.iam_worker.task_role_arn
  log_group_name     = module.log_groups_ecs.log_group_names["worker"]
  container_port     = 0 # pure consumer, no port
  env_vars           = local.common_runtime_env
  secrets            = local.common_runtime_secrets
  tags               = local.common_tags
}

module "ecs_integration" {
  source = "../../modules/ecs_service"

  project            = var.project
  env                = var.env
  service_name       = "integration"
  cluster_id         = module.ecs_cluster.cluster_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.services_id]
  image_uri          = "${module.ecr.repository_urls["integration"]}:bootstrap"
  execution_role_arn = module.iam_integration.execution_role_arn
  task_role_arn      = module.iam_integration.task_role_arn
  log_group_name     = module.log_groups_ecs.log_group_names["integration"]
  container_port     = 8002
  env_vars           = local.common_runtime_env
  secrets            = local.common_runtime_secrets

  load_balancer = var.domain != "" ? {
    target_group_arn = module.alb[0].target_group_arns["integration"]
    container_port   = 8002
  } : null

  tags = local.common_tags
}

module "ecs_api" {
  source = "../../modules/ecs_service"

  project            = var.project
  env                = var.env
  service_name       = "api"
  cluster_id         = module.ecs_cluster.cluster_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.services_id]
  image_uri          = "${module.ecr.repository_urls["api"]}:bootstrap"
  execution_role_arn = module.iam_api.execution_role_arn
  task_role_arn      = module.iam_api.task_role_arn
  log_group_name     = module.log_groups_ecs.log_group_names["api"]
  container_port     = 8003
  env_vars           = local.common_runtime_env
  secrets            = local.common_runtime_secrets

  load_balancer = var.domain != "" ? {
    target_group_arn = module.alb[0].target_group_arns["api"]
    container_port   = 8003
  } : null

  tags = local.common_tags
}

module "ecs_notification" {
  source = "../../modules/ecs_service"

  project            = var.project
  env                = var.env
  service_name       = "notification"
  cluster_id         = module.ecs_cluster.cluster_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.services_id]
  image_uri          = "${module.ecr.repository_urls["notification"]}:bootstrap"
  execution_role_arn = module.iam_notification.execution_role_arn
  task_role_arn      = module.iam_notification.task_role_arn
  log_group_name     = module.log_groups_ecs.log_group_names["notification"]
  container_port     = 0
  env_vars           = local.common_runtime_env
  secrets            = local.common_runtime_secrets
  tags               = local.common_tags
}

# ── Lambda IAM + functions ─────────────────────────────────────────────────
module "iam_lambda_webhook" {
  source = "../../modules/iam_task_role"

  project             = var.project
  env                 = var.env
  service_name        = "webhook-receiver"
  assume_role_service = "lambda.amazonaws.com"
  kms_key_arn         = module.kms.key_arn
  secret_arns         = [module.secrets.rds_master_password_arn, module.secrets.lookup_pepper_arn]
  sqs_send_arns       = [module.sqs.queue_arns["webhook_events"]]
  tags                = local.common_tags
}

module "iam_lambda_presignup" {
  source = "../../modules/iam_task_role"

  project             = var.project
  env                 = var.env
  service_name        = "cognito-presignup"
  assume_role_service = "lambda.amazonaws.com"
  kms_key_arn         = module.kms.key_arn
  secret_arns         = [module.secrets.rds_master_password_arn, module.secrets.lookup_pepper_arn]
  tags                = local.common_tags
}

module "iam_lambda_postconfirm" {
  source = "../../modules/iam_task_role"

  project               = var.project
  env                   = var.env
  service_name          = "cognito-postconfirm"
  assume_role_service   = "lambda.amazonaws.com"
  kms_key_arn           = module.kms.key_arn
  secret_arns           = [module.secrets.rds_master_password_arn, module.secrets.lookup_pepper_arn]
  cognito_user_pool_arn = module.cognito.user_pool_arn
  tags                  = local.common_tags
}

module "iam_lambda_pre_token_gen" {
  source = "../../modules/iam_task_role"

  project             = var.project
  env                 = var.env
  service_name        = "cognito-pre-token-gen"
  assume_role_service = "lambda.amazonaws.com"
  kms_key_arn         = module.kms.key_arn
  secret_arns         = [module.secrets.rds_master_password_arn, module.secrets.lookup_pepper_arn]
  tags                = local.common_tags
}

module "lambda_webhook_receiver" {
  source = "../../modules/container_lambda"

  project                = var.project
  env                    = var.env
  name                   = "webhook-receiver"
  image_uri              = "${module.ecr.repository_urls["webhook-receiver"]}:bootstrap"
  role_arn               = module.iam_lambda_webhook.execution_role_arn
  vpc_subnet_ids         = module.vpc.private_subnet_ids
  vpc_security_group_ids = [module.security_groups.lambda_id]
  log_group_name         = module.log_groups_lambda.log_group_names["webhook-receiver"]
  env_vars = merge(local.common_runtime_env, {
    VIBEROI_SERVICE_NAME = "webhook-receiver"
  })
  tags = local.common_tags
}

module "lambda_cognito_presignup" {
  source = "../../modules/container_lambda"

  project                = var.project
  env                    = var.env
  name                   = "cognito-presignup"
  image_uri              = "${module.ecr.repository_urls["cognito-presignup"]}:bootstrap"
  role_arn               = module.iam_lambda_presignup.execution_role_arn
  vpc_subnet_ids         = module.vpc.private_subnet_ids
  vpc_security_group_ids = [module.security_groups.lambda_id]
  log_group_name         = module.log_groups_lambda.log_group_names["cognito-presignup"]
  env_vars = merge(local.common_runtime_env, {
    VIBEROI_SERVICE_NAME = "cognito-presignup"
    COGNITO_USER_POOL_ID = module.cognito.user_pool_id
  })
  tags = local.common_tags
}

module "lambda_cognito_postconfirm" {
  source = "../../modules/container_lambda"

  project                = var.project
  env                    = var.env
  name                   = "cognito-postconfirm"
  image_uri              = "${module.ecr.repository_urls["cognito-postconfirm"]}:bootstrap"
  role_arn               = module.iam_lambda_postconfirm.execution_role_arn
  vpc_subnet_ids         = module.vpc.private_subnet_ids
  vpc_security_group_ids = [module.security_groups.lambda_id]
  log_group_name         = module.log_groups_lambda.log_group_names["cognito-postconfirm"]
  env_vars = merge(local.common_runtime_env, {
    VIBEROI_SERVICE_NAME = "cognito-postconfirm"
    COGNITO_USER_POOL_ID = module.cognito.user_pool_id
  })
  tags = local.common_tags
}

module "lambda_cognito_pre_token_gen" {
  source = "../../modules/container_lambda"

  project                = var.project
  env                    = var.env
  name                   = "cognito-pre-token-gen"
  image_uri              = "${module.ecr.repository_urls["cognito-pre-token-gen"]}:bootstrap"
  role_arn               = module.iam_lambda_pre_token_gen.execution_role_arn
  vpc_subnet_ids         = module.vpc.private_subnet_ids
  vpc_security_group_ids = [module.security_groups.lambda_id]
  log_group_name         = module.log_groups_lambda.log_group_names["cognito-pre-token-gen"]
  env_vars = merge(local.common_runtime_env, {
    VIBEROI_SERVICE_NAME = "cognito-pre-token-gen"
    COGNITO_USER_POOL_ID = module.cognito.user_pool_id
  })
  tags = local.common_tags
}

# ── API Gateway → webhook receiver ─────────────────────────────────────────
module "api_gateway_webhook" {
  source = "../../modules/api_gateway_webhook"

  project              = var.project
  env                  = var.env
  lambda_function_name = module.lambda_webhook_receiver.function_name
  lambda_invoke_arn    = module.lambda_webhook_receiver.invoke_arn
  tags                 = local.common_tags
}

# ── ACM cert (skipped when domain is empty) ────────────────────────────────
# Covers all the subdomains the platform serves. After apply:
#   terraform output -json acm_validation_records
# Paste the CNAMEs into Hostinger; wait ~30 min for ACM to validate.
module "acm" {
  source = "../../modules/acm_cert"
  count  = var.domain != "" ? 1 : 0

  project = var.project
  env     = var.env
  domain  = var.domain
  subject_alternative_names = [
    "app.${var.domain}",
    "api.${var.domain}",
    "auth.${var.domain}",
    "webhooks.${var.domain}",
  ]
  tags = local.common_tags
}

# ── ALB ────────────────────────────────────────────────────────────────────
# Created regardless of `domain` - the ALB DNS name is always reachable;
# the HTTPS listener attaches the cert only when one exists.
#
# When `domain == ""`, we still create the ALB but skip HTTPS (HTTP only
# isn't acceptable for prod; for dev you can hit the ALB DNS directly
# over the HTTP listener which redirects to HTTPS - and HTTPS will fail
# without a cert. So in practice domain must be set before the ALB is
# useful. Apply the ACM module first.)
module "alb" {
  source = "../../modules/alb"
  count  = var.domain != "" ? 1 : 0

  project            = var.project
  env                = var.env
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.public_subnet_ids
  security_group_ids = [module.security_groups.alb_id]
  certificate_arn    = module.acm[0].certificate_arn

  tags = local.common_tags
}

# ── CloudFront for frontend ────────────────────────────────────────────────
# Defaults to NO custom domain - serves on `<id>.cloudfront.net`. Once
# ACM cert is ISSUED, flip `enable_cloudfront_custom_domain = true`
# and re-apply to attach `app.<domain>`.
module "cloudfront" {
  source = "../../modules/cloudfront_frontend"

  project                              = var.project
  env                                  = var.env
  frontend_bucket_id                   = module.s3.frontend_bucket_id
  frontend_bucket_regional_domain_name = module.s3.frontend_bucket_regional_domain_name
  frontend_bucket_arn                  = module.s3.frontend_bucket_arn

  # Same-origin routing: /api/* hits the ALB, everything else hits S3.
  alb_dns_name = var.domain != "" ? module.alb[0].alb_dns_name : ""

  aliases         = var.enable_cloudfront_custom_domain && var.domain != "" ? ["app.${var.domain}"] : []
  certificate_arn = var.enable_cloudfront_custom_domain && var.domain != "" ? module.acm[0].certificate_arn : null

  tags = local.common_tags
}

# ── Cognito custom domain ──────────────────────────────────────────────────
# Phase 3: only when the cert is ISSUED. Cognito refuses pending certs.
module "cognito_custom_domain" {
  source = "../../modules/cognito_custom_domain"
  count  = var.enable_cognito_custom_domain && var.domain != "" ? 1 : 0

  user_pool_id    = module.cognito.user_pool_id
  domain          = "auth.${var.domain}"
  certificate_arn = module.acm[0].certificate_arn
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
  description = "All Secrets Manager ARNs - task roles get decrypt permission on these in 6D."
  value       = module.secrets.all_secret_arns
}

# ── 6C outputs ─────────────────────────────────────────────────────────────
output "cognito_user_pool_id" {
  description = "Set in backend settings as cognito_user_pool_id."
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_arn" {
  value = module.cognito.user_pool_arn
}

output "cognito_app_client_id" {
  description = "SPA client id - set in backend settings.cognito_app_client_id and in frontend Cognito config."
  value       = module.cognito.spa_client_id
}

output "cognito_user_pool_endpoint" {
  description = "OIDC issuer - matches the iss claim the JWT verifier expects."
  value       = module.cognito.user_pool_endpoint
}

output "cognito_hosted_ui_domain" {
  description = "Login URL = https://<this>/login?client_id=<client_id>&response_type=code&scope=openid+email+profile&redirect_uri=<callback>"
  value       = module.cognito.hosted_ui_domain
}

# ── 6D outputs ─────────────────────────────────────────────────────────────
output "ecr_repository_urls" {
  description = "Map short-name → ECR URL. GitHub Actions docker-pushes to these in 6F."
  value       = module.ecr.repository_urls
}

output "ecs_cluster_name" {
  description = "Cluster name - `aws ecs update-service --cluster <this>` for deploys."
  value       = module.ecs_cluster.cluster_name
}

output "ecs_service_names" {
  description = "Map short-name → ECS service name."
  value = {
    ingest       = module.ecs_ingest.service_name
    worker       = module.ecs_worker.service_name
    integration  = module.ecs_integration.service_name
    api          = module.ecs_api.service_name
    notification = module.ecs_notification.service_name
  }
}

output "lambda_function_names" {
  description = "Map short-name → Lambda function name."
  value = {
    webhook_receiver      = module.lambda_webhook_receiver.function_name
    cognito_presignup     = module.lambda_cognito_presignup.function_name
    cognito_postconfirm   = module.lambda_cognito_postconfirm.function_name
    cognito_pre_token_gen = module.lambda_cognito_pre_token_gen.function_name
  }
}

output "webhook_api_endpoint" {
  description = "Default API Gateway endpoint for inbound webhooks. Paste into GitHub/Jira/Linear webhook config until custom domain is wired in 6E."
  value       = module.api_gateway_webhook.api_endpoint
}

# ── 6E outputs ─────────────────────────────────────────────────────────────
output "acm_certificate_arn" {
  description = "ACM cert ARN, or null if domain not set."
  value       = var.domain != "" ? module.acm[0].certificate_arn : null
}

output "acm_validation_records" {
  description = "DNS records to paste into Hostinger. Map: domain → {record_name, record_value, record_type}. Add each as a CNAME; cert validates within ~30 minutes."
  value       = var.domain != "" ? module.acm[0].domain_validation_options : {}
}

output "acm_certificate_status" {
  description = "PENDING_VALIDATION until the CNAMEs land in Hostinger and AWS rechecks."
  value       = var.domain != "" ? module.acm[0].certificate_status : "n/a"
}

output "alb_dns_name" {
  description = "ALB hostname. CNAME api.<domain> here at Hostinger."
  value       = var.domain != "" ? module.alb[0].alb_dns_name : null
}

output "cloudfront_domain_name" {
  description = "CloudFront `.cloudfront.net` hostname. CNAME app.<domain> here at Hostinger (once enable_cloudfront_custom_domain is true)."
  value       = module.cloudfront.distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "Used by the GitHub Actions deploy pipeline to invalidate cache."
  value       = module.cloudfront.distribution_id
}

output "cognito_custom_domain_target" {
  description = "Underlying CloudFront ARN behind the Cognito custom domain (auth.<domain>). CNAME auth.<domain> to the CloudFront distribution at Hostinger once enable_cognito_custom_domain is true."
  value       = var.enable_cognito_custom_domain && var.domain != "" ? module.cognito_custom_domain[0].cloudfront_distribution : null
}

# Convenient summary of DNS records you need to add at Hostinger.
# Both branches return a map so terraform can plan a consistent type;
# when `var.domain` is unset the map carries a single explanatory entry.
output "hostinger_dns_records_needed" {
  description = "Human-readable summary of every DNS record the user needs to add. Lists only the records relevant to the currently-enabled toggles."
  value = var.domain == "" ? {
    "set var.domain to see DNS records" = ""
    } : merge(
    {
      "ACM validation (one CNAME per name in the cert, see acm_validation_records output)" = "see acm_validation_records output"
    },
    {
      "api.${var.domain} (CNAME → ALB)" = module.alb[0].alb_dns_name
    },
    var.enable_cloudfront_custom_domain ? {
      "app.${var.domain} (CNAME → CloudFront)" = module.cloudfront.distribution_domain_name
    } : {},
    var.enable_cognito_custom_domain ? {
      "auth.${var.domain} (CNAME → Cognito CloudFront)" = "see cognito_custom_domain_target output"
    } : {},
    {
      "webhooks.${var.domain} (CNAME → API Gateway)" = trimprefix(module.api_gateway_webhook.api_endpoint, "https://")
    },
  )
}

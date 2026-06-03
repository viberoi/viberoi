# Base security groups for the platform.
#
# Pattern: one SG per role (alb, services, lambda, rds, redis). Cross-tier
# rules reference SG ids, not CIDRs, so a subnet-CIDR change in the VPC
# doesn't ripple into SG rules.
#
# Egress is `0.0.0.0/0` by default — services need to reach the
# internet (Cognito, KMS, Slack, etc.) via the NAT gateway. Inbound is
# strictly scoped.
#
# RDS + Redis allow inbound ONLY from `services` + `lambda` SGs. The
# ALB cannot reach the DB layer.

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "security_groups"
    },
    var.tags,
  )
}

# ── ALB ─────────────────────────────────────────────────────────────────────
# Public-facing — accepts 80 + 443 from anywhere; 80 redirects to 443.
resource "aws_security_group" "alb" {
  name        = "${local.prefix}-sg-alb"
  description = "Public ALB — accepts 80/443 from anywhere."
  vpc_id      = var.vpc_id

  tags = merge(local.common_tags, { Name = "${local.prefix}-sg-alb" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow inbound HTTP (redirects to HTTPS at listener)."
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow inbound HTTPS."
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  description       = "ALB needs to reach target containers in services SG."
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# ── ECS services ───────────────────────────────────────────────────────────
# All Fargate tasks (ingest, api, integration, worker, notification) live
# behind one SG. Containers expose 8001–8003 on their tasks; the ALB
# targets those ports per service. Internal — accepts inbound only from
# the ALB SG.
resource "aws_security_group" "services" {
  name        = "${local.prefix}-sg-services"
  description = "ECS Fargate services — inbound from ALB only."
  vpc_id      = var.vpc_id

  tags = merge(local.common_tags, { Name = "${local.prefix}-sg-services" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "services_from_alb" {
  security_group_id            = aws_security_group.services.id
  description                  = "All container ports — ALB targets pick the port per service."
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8999
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_egress_rule" "services_all" {
  security_group_id = aws_security_group.services.id
  description       = "Outbound — Cognito, KMS, S3, SQS, Slack, etc. via NAT."
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# ── Lambda ─────────────────────────────────────────────────────────────────
# Container-image Lambdas in the VPC (webhook receiver, Cognito triggers).
# No inbound; egress same as services.
resource "aws_security_group" "lambda" {
  name        = "${local.prefix}-sg-lambda"
  description = "VPC-attached Lambdas — no inbound, full egress."
  vpc_id      = var.vpc_id

  tags = merge(local.common_tags, { Name = "${local.prefix}-sg-lambda" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_egress_rule" "lambda_all" {
  security_group_id = aws_security_group.lambda.id
  description       = "Outbound — RDS, KMS, SQS via NAT or endpoints."
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# ── RDS ────────────────────────────────────────────────────────────────────
# Postgres 5432. Inbound from services + lambda SGs only.
resource "aws_security_group" "rds" {
  name        = "${local.prefix}-sg-rds"
  description = "RDS Postgres — inbound 5432 from services + lambda."
  vpc_id      = var.vpc_id

  tags = merge(local.common_tags, { Name = "${local.prefix}-sg-rds" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_services" {
  security_group_id            = aws_security_group.rds.id
  description                  = "Postgres from ECS services."
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.services.id
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_lambda" {
  security_group_id            = aws_security_group.rds.id
  description                  = "Postgres from VPC Lambdas."
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.lambda.id
}

# Egress none — DB doesn't initiate outbound.
resource "aws_vpc_security_group_egress_rule" "rds_none" {
  security_group_id = aws_security_group.rds.id
  description       = "No egress — DB doesn't initiate connections."
  ip_protocol       = "-1"
  cidr_ipv4         = "127.0.0.1/32"
}

# ── Redis ──────────────────────────────────────────────────────────────────
# ElastiCache 6379. Inbound from services + lambda SGs only.
resource "aws_security_group" "redis" {
  name        = "${local.prefix}-sg-redis"
  description = "ElastiCache Redis — inbound 6379 from services + lambda."
  vpc_id      = var.vpc_id

  tags = merge(local.common_tags, { Name = "${local.prefix}-sg-redis" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_services" {
  security_group_id            = aws_security_group.redis.id
  description                  = "Redis from ECS services."
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
  referenced_security_group_id = aws_security_group.services.id
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_lambda" {
  security_group_id            = aws_security_group.redis.id
  description                  = "Redis from VPC Lambdas."
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
  referenced_security_group_id = aws_security_group.lambda.id
}

resource "aws_vpc_security_group_egress_rule" "redis_none" {
  security_group_id = aws_security_group.redis.id
  description       = "No egress."
  ip_protocol       = "-1"
  cidr_ipv4         = "127.0.0.1/32"
}

# RDS Postgres for the platform.
#
# Master user is `postgres` (the AWS default). Post-apply, run the
# bootstrap SQL (analogue of scripts/postgres-init.sql) to create the
# `viberoi` runtime role + `viberoi_admin` migration role. Alembic
# migrations then run with `viberoi_admin` as usual.
#
# Storage is KMS-encrypted with the env CMK (matches the same CMK used
# for application PII at rest — no second key to manage).

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "rds"
    },
    var.tags,
  )
}

resource "aws_db_subnet_group" "this" {
  name        = "${local.prefix}-pg-subnet-group"
  description = "Subnet group for the env Postgres instance."
  subnet_ids  = var.data_subnet_ids

  tags = merge(local.common_tags, { Name = "${local.prefix}-pg-subnet-group" })
}

resource "aws_db_parameter_group" "this" {
  name        = "${local.prefix}-pg16"
  family      = "postgres16"
  description = "${local.prefix} Postgres params — RLS-friendly defaults."

  # `force_ssl=1` so non-TLS connections are refused. Library defaults
  # to SSL already; this is belt-and-braces.
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # log queries > 1s
  }

  tags = local.common_tags
}

resource "aws_db_instance" "this" {
  identifier = "${local.prefix}-pg"

  engine               = "postgres"
  engine_version       = var.engine_version
  instance_class       = var.instance_class
  parameter_group_name = aws_db_parameter_group.this.name

  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.max_allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = var.kms_key_arn

  db_name  = "viberoi"
  username = "postgres"
  password = var.master_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = var.security_group_ids
  publicly_accessible    = false

  multi_az                = var.multi_az
  backup_retention_period = var.backup_retention_days
  backup_window           = "06:00-06:30" # UTC
  maintenance_window      = "sun:07:00-sun:07:30"

  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.prefix}-pg-final"

  performance_insights_enabled    = false
  enabled_cloudwatch_logs_exports = ["postgresql"]

  apply_immediately = false

  tags = merge(local.common_tags, { Name = "${local.prefix}-pg" })
}

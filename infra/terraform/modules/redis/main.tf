# ElastiCache Redis (replication group — single-node when num_cache_clusters=1).
#
# At-rest + in-transit encryption on. No auth token for V1 — VPC SG
# already restricts to services/lambda. Auth token complicates the
# Python client and adds rotation overhead; skip until a real audit
# demand surfaces.

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "redis"
    },
    var.tags,
  )
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "${local.prefix}-redis-subnet-group"
  subnet_ids = var.data_subnet_ids

  tags = local.common_tags
}

resource "aws_elasticache_parameter_group" "this" {
  name   = "${local.prefix}-redis7"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru" # Redis is a cache — evict LRU when memory full
  }

  tags = local.common_tags
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${local.prefix}-redis"
  description          = "${local.prefix} Redis"

  node_type            = var.node_type
  engine_version       = var.engine_version
  parameter_group_name = aws_elasticache_parameter_group.this.name

  num_cache_clusters         = var.num_cache_clusters
  automatic_failover_enabled = var.num_cache_clusters > 1
  multi_az_enabled           = var.num_cache_clusters > 1

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = var.security_group_ids

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = var.kms_key_arn

  snapshot_retention_limit = 1
  snapshot_window          = "06:30-07:00"
  maintenance_window       = "sun:07:30-sun:08:00"

  tags = merge(local.common_tags, { Name = "${local.prefix}-redis" })
}

# ECS Fargate cluster.
#
# One cluster per env. Container Insights is on - gives us per-task
# CPU/memory/network metrics in CloudWatch for the alarms in 6F.
# Capacity providers: FARGATE (always-on) + FARGATE_SPOT (cheaper for
# workers that tolerate eviction; defer using it until prod).

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "ecs_cluster"
    },
    var.tags,
  )
}

resource "aws_ecs_cluster" "this" {
  name = "${local.prefix}-ecs"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, { Name = "${local.prefix}-ecs" })
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

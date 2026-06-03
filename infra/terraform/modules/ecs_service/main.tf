# Reusable ECS Fargate service.
#
# Used once per backend service (ingest / worker / integration / api /
# notification). Pattern:
#
#   1. Task definition with one container, the image, log group,
#      env vars, and secrets refs.
#   2. Service that runs `desired_count` tasks in the private subnets
#      with the services SG.
#   3. Optional load balancer attachment for HTTP services.
#
# `desired_count` defaults to 0 so first apply doesn't fail on
# "image not found" before the GitHub Actions pipeline (6F) pushes.
# Bump to ≥1 once the image is in ECR.

locals {
  prefix = "${var.project}-${var.env}-${var.service_name}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "ecs_service"
      Service   = var.service_name
    },
    var.tags,
  )

  port_mappings = var.container_port > 0 ? [
    {
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }
  ] : []

  env_vars_array = [
    for k, v in var.env_vars : { name = k, value = v }
  ]

  secrets_array = [
    for k, v in var.secrets : { name = k, valueFrom = v }
  ]
}

data "aws_region" "current" {}

# ── Task definition ────────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "this" {
  family                   = local.prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = var.service_name
      image     = var.image_uri
      essential = true
      command   = var.command

      portMappings = local.port_mappings

      environment = local.env_vars_array
      secrets     = local.secrets_array

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.log_group_name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = var.service_name
        }
      }
    }
  ])

  tags = merge(local.common_tags, { Name = local.prefix })
}

# ── Service ────────────────────────────────────────────────────────────────
resource "aws_ecs_service" "this" {
  name            = local.prefix
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = var.load_balancer != null ? [var.load_balancer] : []
    content {
      target_group_arn = load_balancer.value.target_group_arn
      container_name   = var.service_name
      container_port   = load_balancer.value.container_port
    }
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  # When GitHub Actions updates the task def via `aws ecs update-service`,
  # don't fight it on `desired_count` — leave that to the runtime owner.
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = merge(local.common_tags, { Name = local.prefix })
}

# Application Load Balancer + HTTPS listener + per-service target groups.
#
# Three HTTP backend services share one host (api.<domain>) with
# path-based routing:
#   /ingest/*  + /agent/*    → ingest service     :8001
#   /integrations/*          → integration service :8002
#   everything else (default) → api service        :8003
#
# Worker + notification are pure consumers and don't go behind the ALB.
#
# HTTP listener redirects 80→443. HTTPS uses the env's ACM cert; while
# the cert is in PENDING_VALIDATION the listener exists but won't serve
# HTTPS until validation completes.

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "alb"
    },
    var.tags,
  )

  # Service whose path_patterns is ["*"] becomes the default - the rule
  # with the highest priority number, AND the listener's default_action.
  default_service = [
    for k, v in var.services : k if length(v.path_patterns) == 1 && v.path_patterns[0] == "*"
  ][0]
}

# ── ALB ────────────────────────────────────────────────────────────────────
resource "aws_lb" "this" {
  name               = "${local.prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.subnet_ids
  security_groups    = var.security_group_ids

  drop_invalid_header_fields = true

  enable_deletion_protection = false # dev - flip true in prod

  tags = merge(local.common_tags, { Name = "${local.prefix}-alb" })
}

# ── Target groups (one per service) ────────────────────────────────────────
resource "aws_lb_target_group" "this" {
  for_each = var.services

  name        = "${local.prefix}-tg-${each.key}"
  port        = each.value.container_port
  protocol    = "HTTP"
  target_type = "ip" # Fargate
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    path                = each.value.health_path
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30

  tags = merge(local.common_tags, {
    Name    = "${local.prefix}-tg-${each.key}"
    Service = each.key
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ── HTTP listener - redirect to HTTPS ──────────────────────────────────────
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ── HTTPS listener ─────────────────────────────────────────────────────────
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this[local.default_service].arn
  }
}

# ── Listener rules - one per non-default service ──────────────────────────
resource "aws_lb_listener_rule" "service" {
  for_each = {
    for k, v in var.services : k => v if k != local.default_service
  }

  listener_arn = aws_lb_listener.https.arn
  priority     = each.value.priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this[each.key].arn
  }

  condition {
    path_pattern {
      values = each.value.path_patterns
    }
  }
}

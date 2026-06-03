# HTTP API v2 → Lambda integration for inbound webhooks.
#
# Route: ANY /webhooks/{provider}/{integration_id}
# (matches `_PATH_RE` in webhook_receiver/handler.py)
#
# CORS is left default — webhook callers don't run in browsers, so no
# preflight needed.
#
# The API Gateway base URL is what we paste into GitHub/Jira/Linear
# webhook config. Custom domain (webhooks.<env>.<domain>) lands in 6E.

locals {
  prefix = "${var.project}-${var.env}-webhooks"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "api_gateway_webhook"
    },
    var.tags,
  )
}

# ── HTTP API ───────────────────────────────────────────────────────────────
resource "aws_apigatewayv2_api" "this" {
  name          = local.prefix
  protocol_type = "HTTP"
  description   = "Inbound webhooks from GitHub / GitLab / Linear → webhook_receiver Lambda."

  tags = local.common_tags
}

# Lambda proxy integration — passes the raw request through, body
# included, so the Lambda can compute HMAC over the exact bytes.
resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.this.id
  integration_type = "AWS_PROXY"
  integration_uri  = var.lambda_invoke_arn

  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}

resource "aws_apigatewayv2_route" "webhooks" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "ANY /webhooks/{provider}/{integration_id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ── Access logs ────────────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "access" {
  name              = "/aws/apigatewayv2/${local.prefix}/access"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, { Name = "/aws/apigatewayv2/${local.prefix}/access" })
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.access.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      lambdaError    = "$context.integration.error"
    })
  }

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 200
  }

  tags = local.common_tags
}

# ── Allow API Gateway to invoke the Lambda ─────────────────────────────────
resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"

  # Source ARN scoped to ALL stages/routes under this API.
  source_arn = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}

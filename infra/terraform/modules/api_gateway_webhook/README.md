# api_gateway_webhook

HTTP API v2 fronting the `webhook_receiver` Lambda.

- Route: `ANY /webhooks/{provider}/{integration_id}` — matches the
  Lambda's path regex.
- Lambda proxy integration with `payload_format_version = "2.0"` so
  the Lambda gets the raw body for HMAC verification.
- Access logs to a CloudWatch group with 30-day retention.
- Throttle: 200 req/s, 100 burst — webhook providers respect 4xx,
  this floor stops a single tenant from drowning the consumer.

Default endpoint format:
`https://<api-id>.execute-api.us-east-1.amazonaws.com`

6E wires a custom domain (`webhooks.<env>.<domain>`).

## Inputs

| name | notes |
|---|---|
| `lambda_function_name` | webhook receiver function name |
| `lambda_invoke_arn` | webhook receiver invoke ARN |
| `log_retention_days` | default 30 |

## Outputs

`api_id`, `api_endpoint`, `execution_arn`.

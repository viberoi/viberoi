# iam_task_role

Per-service IAM roles. Returns two:

- **execution_role** — used by ECS / Lambda to pull the image, write
  to CloudWatch logs, fetch Secrets Manager values into the task's
  `secrets` block. ECS gets `AmazonECSTaskExecutionRolePolicy`;
  Lambda gets `AWSLambdaBasicExecutionRole` + `AWSLambdaVPCAccessExecutionRole`.
- **task_role** — used by the running container / Lambda. Scoped to
  exactly the AWS APIs the service needs.

## Per-service policy menu

| Variable | Effect |
|---|---|
| `kms_key_arn` | encrypt/decrypt on the env CMK (always) |
| `secret_arns` | GetSecretValue + DescribeSecret on these ARNs only |
| `sqs_send_arns` | SendMessage on these queues |
| `sqs_receive_arns` | ReceiveMessage / DeleteMessage / ChangeVisibility on these queues |
| `s3_read_arns` | ListBucket + GetObject (objects auto-suffixed `/*`) |
| `s3_write_arns` | ListBucket + PutObject + DeleteObject |
| `cognito_user_pool_arn` | AdminUpdateUserAttributes + AdminGetUser. Only PostConfirmation Lambda needs this. |

## ECS vs Lambda

Pass `assume_role_service = "lambda.amazonaws.com"` for Lambdas. The
module automatically swaps the AWS-managed policies. Everything else
stays the same — task role permissions are identical in shape.

## Outputs

`execution_role_arn`, `task_role_arn` + name variants.

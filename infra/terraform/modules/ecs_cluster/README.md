# ecs_cluster

One Fargate cluster per env. Container Insights enabled.

Capacity providers: FARGATE (default) + FARGATE_SPOT (available but
not the default in dev — flip to spot in workers once we trust their
restart-on-eviction behaviour).

## Outputs

`cluster_id`, `cluster_name`, `cluster_arn`.

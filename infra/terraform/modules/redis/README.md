# redis

ElastiCache Redis replication group.

| Default | Value |
|---|---|
| Node type | `cache.t4g.micro` |
| Engine | Redis 7.1 |
| Nodes | 1 (single-node; bump for replicas) |
| At-rest encryption | KMS CMK |
| In-transit encryption | on |
| Auth token | off (SG-only; revisit) |
| Maxmemory policy | `allkeys-lru` |

## Inputs

| name | default | notes |
|---|---|---|
| `data_subnet_ids` | | from modules/vpc |
| `security_group_ids` | | `[modules/security_groups.redis_id]` |
| `kms_key_arn` | | from modules/kms |
| `node_type` | `cache.t4g.micro` | bump for prod |
| `num_cache_clusters` | 1 | 2+ enables auto-failover + multi-AZ |

## Outputs

`primary_endpoint_address`, `reader_endpoint_address`, `port`, `replication_group_id`.

Connect with `rediss://<primary_endpoint_address>:<port>/0` —
transit_encryption_enabled means TLS is required.

## Cost

~$9/mo for `cache.t4g.micro` single-node. ~doubles per added node.

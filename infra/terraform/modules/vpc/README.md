# vpc

VPC with public / private / data subnet tiers across N AZs.

```
public  → ALB + NAT
private → ECS Fargate, Lambdas (egress via NAT)
data    → RDS + ElastiCache (no egress)
```

## Inputs

| name | default | notes |
|---|---|---|
| `project` | `viberoi` | name prefix |
| `env` | — | `dev`/`staging`/`prod` |
| `cidr_block` | `10.20.0.0/16` | /16 carves into /20 subnets |
| `az_count` | `2` | bump to `3` for prod durability |
| `single_nat` | `true` | one NAT for cost (dev); set `false` in prod for HA |
| `enable_vpc_endpoints` | `false` | adds S3 + DynamoDB gateway endpoints (free). Set true to cut NAT egress costs. |

## Outputs

`vpc_id`, `vpc_cidr_block`, `public_subnet_ids`, `private_subnet_ids`,
`data_subnet_ids`, `availability_zones`, `nat_gateway_ids`.

## Cost shape (dev defaults)

- 1 NAT gateway: ~$32/mo + data
- 1 EIP for NAT: ~$0 while attached
- VPC + subnets + route tables: free
- VPC endpoints (if enabled): gateway endpoints free; interface endpoints ~$7/mo each

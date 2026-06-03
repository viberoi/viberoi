# security_groups

Base SGs for the platform. One per role; cross-tier rules reference SG
ids (not CIDRs), so subnet renumbering doesn't ripple.

| SG | Inbound | Egress |
|---|---|---|
| `alb` | 80, 443 from `0.0.0.0/0` | unrestricted (to targets) |
| `services` | 8000–8999 from `alb` | unrestricted (NAT) |
| `lambda` | none | unrestricted (NAT) |
| `rds` | 5432 from `services` + `lambda` | none |
| `redis` | 6379 from `services` + `lambda` | none |

Egress from `rds` / `redis` is pinned to `127.0.0.1/32` as a no-op
placeholder — Terraform demands at least one egress rule. The DBs
never initiate outbound.

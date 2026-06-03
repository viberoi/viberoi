# rds

Postgres 16 for the platform.

| Default | Value |
|---|---|
| Instance | `db.t4g.micro` |
| Storage | 20 GB gp3, autoscale to 100 GB |
| Multi-AZ | off (dev); flip in prod |
| Backups | 7 days, 06:00–06:30 UTC |
| Maintenance | Sun 07:00–07:30 UTC |
| TLS | enforced (`rds.force_ssl=1`) |
| Encryption | KMS CMK from modules/kms |
| Deletion protection | on |

## Post-apply bootstrap

The RDS master is `postgres`. Run the role bootstrap SQL (analogue of
`scripts/postgres-init.sql`) before Alembic migrations:

```sql
CREATE ROLE viberoi_admin LOGIN PASSWORD '<from Secrets Manager>' BYPASSRLS;
CREATE ROLE viberoi LOGIN PASSWORD '<from Secrets Manager>' NOBYPASSRLS;
GRANT CONNECT ON DATABASE viberoi TO viberoi_admin, viberoi;
GRANT USAGE, CREATE ON SCHEMA public TO viberoi_admin;
GRANT USAGE ON SCHEMA public TO viberoi;
ALTER DEFAULT PRIVILEGES FOR ROLE viberoi_admin IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO viberoi;
ALTER DEFAULT PRIVILEGES FOR ROLE viberoi_admin IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO viberoi;
```

Connect via Session Manager port forwarding or a bastion in 6D once
that ECS task exists. For now, one-time tunnel through a temporary EC2
or a Session Manager-enabled task.

Then point Alembic at the new instance and `alembic upgrade head`.

## Inputs

| name | default | notes |
|---|---|---|
| `data_subnet_ids` | | from modules/vpc |
| `security_group_ids` | | `[modules/security_groups.rds_id]` |
| `kms_key_arn` | | from modules/kms |
| `master_password` | | from modules/secrets — `random_password.rds_master.result` |
| `instance_class` | `db.t4g.micro` | bump for prod |
| `multi_az` | `false` | true in staging+ |
| `backup_retention_days` | 7 | 30 in prod |
| `deletion_protection` | `true` | never set false in prod |
| `skip_final_snapshot` | `false` | true only if destroying dev intentionally |

## Outputs

`endpoint`, `address`, `port`, `db_name`, `master_username`, `id`, `arn`.

## Cost

~$13/mo for `db.t4g.micro` single-AZ + storage. Multi-AZ ~doubles it.

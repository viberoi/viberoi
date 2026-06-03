# ecr

One ECR repo per service / Lambda — created via `for_each` over a list.

- `image_tag_mutability = IMMUTABLE` — once a tag is pushed, it can't be
  overwritten. Forces deterministic deploys.
- `scan_on_push = true` — image scanning on every push.
- KMS-encrypted with the env CMK.

## Lifecycle

| Rule | What |
|---|---|
| Priority 1 | Keep newest 30 tagged images |
| Priority 2 | Expire untagged after 14 days |

## Inputs

| name | notes |
|---|---|
| `repo_names` | list of short names. Final = `${project}-${env}-<name>`. |
| `kms_key_arn` | from modules/kms |

## Outputs

`repository_urls`, `repository_arns`, `repository_names` — all keyed
by short name.

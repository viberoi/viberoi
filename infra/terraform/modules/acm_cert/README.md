# acm_cert

ACM certificate covering apex + N SANs, DNS-validated.

## How validation works

DNS is at Hostinger. AWS publishes a CNAME-per-domain it wants you to
prove ownership of. After this module's apply:

```bash
terraform output -json domain_validation_options
```

You'll see:

```json
{
  "app.viberoi.io": {
    "record_name": "_a1b2c3.app.viberoi.io.",
    "record_value": "_d4e5f6.xyz.acm-validations.aws.",
    "record_type": "CNAME"
  },
  ...
}
```

Paste each `record_name → record_value` as a CNAME in Hostinger.
AWS validates within ~30 minutes. Cert status flips to `ISSUED`.

## Why we skip `aws_acm_certificate_validation`

That resource blocks on apply until validation completes. Since we
can't create the validation records ourselves (Hostinger isn't
Terraform-managed), `apply` would hang forever waiting for user action.
We accept the cert in PENDING_VALIDATION state and let validation
happen out-of-band.

## ALB vs CloudFront with pending cert

- **ALB** — happy to attach an unvalidated cert. HTTPS just won't
  serve traffic until validation completes.
- **CloudFront** — refuses an unvalidated cert at create time.

For CloudFront, validate the cert first, THEN apply CloudFront.

## Inputs

| name | notes |
|---|---|
| `domain` | apex — e.g. `viberoi.io` |
| `subject_alternative_names` | every other name to cover |

## Outputs

`certificate_arn`, `domain_validation_options`, `certificate_status`.

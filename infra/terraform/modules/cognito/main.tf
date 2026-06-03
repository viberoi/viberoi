# Cognito user pool + app client + hosted-UI domain.
#
# Tier: ESSENTIALS — free for the first 50k MAU/month, required for the
# PreTokenGeneration v2 trigger that injects custom claims into the
# access token (Slice 5A: we verify access tokens, not ID tokens).
#
# Custom attributes — mutable so the PostConfirmation Lambda can write
# them back via `AdminUpdateUserAttributes` after row provisioning.
#
# Federated IdPs (Google, GitHub OIDC) are conditional: empty creds →
# IdP block isn't created. Native email + OTP works regardless.

locals {
  prefix = "${var.project}-${var.env}"

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "cognito"
    },
    var.tags,
  )

  create_google = var.google_client_id != "" && var.google_client_secret != ""
  create_github = var.github_oidc_client_id != "" && var.github_oidc_client_secret != ""

  supported_idps = concat(
    ["COGNITO"],
    local.create_google ? ["Google"] : [],
    local.create_github ? ["GitHub"] : [],
  )

  # Lambda triggers — only emit blocks for the ones that are wired.
  has_any_trigger = (
    var.lambda_pre_signup_arn != null ||
    var.lambda_post_confirmation_arn != null ||
    var.lambda_pre_token_generation_arn != null
  )
}

# ── User pool ──────────────────────────────────────────────────────────────
resource "aws_cognito_user_pool" "this" {
  name = "${local.prefix}-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  deletion_protection      = var.deletion_protection

  # ESSENTIALS — required for PreTokenGeneration v2 (custom claims in
  # access token). Free up to 50k MAU/month.
  user_pool_tier = "ESSENTIALS"

  # Required attributes — email is the sign-in handle.
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = false
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 5
      max_length = 254
    }
  }

  # Custom attributes — the PostConfirmation Lambda writes these via
  # AdminUpdateUserAttributes after creating the org + developer rows.
  schema {
    name                     = "org_id"
    attribute_data_type      = "String"
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 36
      max_length = 36
    }
  }

  schema {
    name                     = "developer_id"
    attribute_data_type      = "String"
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 36
      max_length = 36
    }
  }

  schema {
    name                     = "role"
    attribute_data_type      = "String"
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 32
    }
  }

  schema {
    name                     = "team_id"
    attribute_data_type      = "String"
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 0
      max_length = 36
    }
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  mfa_configuration = "OFF" # V1; TOTP-optional opt-in later

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Your VibeROI verification code"
    email_message        = "Your verification code is {####}"
  }

  # Conditional lambda_config — only emit when at least one trigger ARN
  # is wired. Module accepts nulls in 6C and gets real ARNs in 6D.
  dynamic "lambda_config" {
    for_each = local.has_any_trigger ? [1] : []
    content {
      pre_sign_up       = var.lambda_pre_signup_arn
      post_confirmation = var.lambda_post_confirmation_arn
      pre_token_generation_config {
        lambda_arn     = var.lambda_pre_token_generation_arn
        lambda_version = "V2_0"
      }
    }
  }

  tags = merge(local.common_tags, { Name = "${local.prefix}-users" })

  # Schema changes after creation are not allowed by Cognito. lifecycle
  # ignores avoid Terraform fighting AWS-side drift on advanced security.
  lifecycle {
    ignore_changes = [schema]
  }
}

# ── Hosted-UI domain ───────────────────────────────────────────────────────
# Cognito-provided subdomain: `<prefix>-<env>.auth.us-east-1.amazoncognito.com`.
# Custom domain (auth.<your-domain>) lands in 6E when the ACM cert exists.
resource "aws_cognito_user_pool_domain" "this" {
  domain       = "${local.prefix}-${random_id.domain_suffix.hex}"
  user_pool_id = aws_cognito_user_pool.this.id
}

# Random suffix so a destroyed-then-recreated pool can re-use the same
# domain name without colliding with the global Cognito namespace
# during the deletion-grace window.
resource "random_id" "domain_suffix" {
  byte_length = 2
}

# ── Federated IdPs (conditional) ───────────────────────────────────────────
resource "aws_cognito_identity_provider" "google" {
  count = local.create_google ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.this.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
    authorize_scopes = "openid email profile"
  }

  attribute_mapping = {
    email          = "email"
    email_verified = "email_verified"
    name           = "name"
    username       = "sub"
  }
}

resource "aws_cognito_identity_provider" "github" {
  count = local.create_github ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.this.id
  provider_name = "GitHub"
  provider_type = "OIDC"

  provider_details = {
    client_id                 = var.github_oidc_client_id
    client_secret             = var.github_oidc_client_secret
    attributes_request_method = "GET"
    authorize_scopes          = "openid user:email"
    oidc_issuer               = "https://token.actions.githubusercontent.com"
    authorize_url             = "https://github.com/login/oauth/authorize"
    token_url                 = "https://github.com/login/oauth/access_token"
    attributes_url            = "https://api.github.com/user"
    jwks_uri                  = "https://token.actions.githubusercontent.com/.well-known/jwks"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
}

# ── App client (public SPA — no client_secret) ─────────────────────────────
resource "aws_cognito_user_pool_client" "spa" {
  name         = "${local.prefix}-spa"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = false # SPA — can't keep a secret

  # USER_SRP_AUTH for password sign-in; REFRESH_TOKEN_AUTH for renewal.
  # USER_PASSWORD_AUTH explicitly OFF — SRP only.
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"

  access_token_validity  = var.access_token_validity_hours
  id_token_validity      = var.id_token_validity_hours
  refresh_token_validity = var.refresh_token_validity_days
  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  supported_identity_providers = local.supported_idps

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  # Custom-attribute read/write — required so PostConfirmation can update
  # the user. `email_verified` write is also required.
  read_attributes = [
    "email",
    "email_verified",
    "custom:org_id",
    "custom:developer_id",
    "custom:role",
    "custom:team_id",
  ]
  write_attributes = [
    "email",
    "custom:org_id",
    "custom:developer_id",
    "custom:role",
    "custom:team_id",
  ]

  # Federated providers attached after pool resources are created so the
  # client's `supported_identity_providers` reference resolves cleanly.
  depends_on = [
    aws_cognito_identity_provider.google,
    aws_cognito_identity_provider.github,
  ]
}

# ── Lambda permissions (only when trigger ARNs are wired) ──────────────────
# Cognito invokes the trigger Lambdas — they need permission to be invoked
# by Cognito. These are no-ops when the ARNs are null (6C).
resource "aws_lambda_permission" "cognito_pre_signup" {
  count = var.lambda_pre_signup_arn != null ? 1 : 0

  statement_id  = "AllowCognitoPreSignUpInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_pre_signup_arn
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.this.arn
}

resource "aws_lambda_permission" "cognito_post_confirmation" {
  count = var.lambda_post_confirmation_arn != null ? 1 : 0

  statement_id  = "AllowCognitoPostConfirmationInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_post_confirmation_arn
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.this.arn
}

resource "aws_lambda_permission" "cognito_pre_token_generation" {
  count = var.lambda_pre_token_generation_arn != null ? 1 : 0

  statement_id  = "AllowCognitoPreTokenGenerationInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_pre_token_generation_arn
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.this.arn
}

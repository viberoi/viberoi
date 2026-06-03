variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "callback_urls" {
  type        = list(string)
  description = "Allowed post-login redirect URLs. Must include the frontend's /auth/callback for every domain it runs on."
  default     = ["http://localhost:5173/auth/callback"]
}

variable "logout_urls" {
  type        = list(string)
  description = "Allowed post-logout redirect URLs."
  default     = ["http://localhost:5173/"]
}

# ── Lambda triggers (wired in 6D once images exist) ────────────────────────
variable "lambda_pre_signup_arn" {
  type        = string
  description = "PreSignUp trigger ARN. Null until 6D ships the container image."
  default     = null
}

variable "lambda_post_confirmation_arn" {
  type        = string
  description = "PostConfirmation trigger ARN. Null until 6D."
  default     = null
}

variable "lambda_pre_token_generation_arn" {
  type        = string
  description = "PreTokenGeneration v2 trigger ARN — injects custom:org_id / role / team_id / developer_id into the access token. Null until 6D."
  default     = null
}

# ── Federated IdPs (optional) ──────────────────────────────────────────────
# When these are empty the corresponding IdP isn't created.
variable "google_client_id" {
  type    = string
  default = ""
}

variable "google_client_secret" {
  type      = string
  sensitive = true
  default   = ""
}

variable "github_oidc_client_id" {
  type    = string
  default = ""
}

variable "github_oidc_client_secret" {
  type      = string
  sensitive = true
  default   = ""
}

# ── Token validities ───────────────────────────────────────────────────────
variable "access_token_validity_hours" {
  type    = number
  default = 1
}

variable "id_token_validity_hours" {
  type    = number
  default = 1
}

variable "refresh_token_validity_days" {
  type    = number
  default = 30
}

variable "deletion_protection" {
  type        = string
  description = "ACTIVE in prod, INACTIVE in dev for easy teardown."
  default     = "INACTIVE"
}

variable "tags" {
  type    = map(string)
  default = {}
}

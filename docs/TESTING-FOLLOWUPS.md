# Testing follow-ups

Things shipped without full hands-on verification. Burn this list down
as you exercise each flow in a real browser / real shell.

## Untested end-to-end

- [ ] **Invite a teammate** — Settings → Team → enter `@rapyder.com` email →
  verify Cognito sends the email, invitee can sign in with the temp password,
  Cognito forces password change, they land on dashboard as Developer in your
  org. Commit `0a8d9ad`.
- [ ] **Logout button** — sidebar bottom-left → confirm redirect to Cognito
  `/logout`, cookie cleared, next signin re-prompts for password. Wired in
  `auth/AuthContext.tsx` + `auth/cognito.ts`. Commit `2cf8743`.
- [ ] **AuthCallback StrictMode fix** — second signin attempt should not
  show "PKCE verifier missing" anymore. Commit `2cf8743`.
- [ ] **204 No Content handling** — `DELETE /notifications/channels/<x>` and
  `DELETE /integrations/<provider>` should resolve cleanly in the UI (no
  JSON-parse error in console). Commit `43ea1ee`.
- [ ] **Cost figures** — pick one of your Opus sessions on the dashboard,
  cross-check against `(input × 15 + output × 75) / 1M` per Anthropic
  public pricing. Should match what's shown. Commit `51a832e`.

## Known gaps to revisit later

- [ ] **Self-signup without invite** — anyone hitting Hosted UI directly still
  needs `scripts/bootstrap-cognito-user.py` run for them. Unblock by deploying
  the PostConfirmation Lambda.
- [ ] **Cost for subscription users** — flagged `is_estimated=true`; figure
  is "equivalent API cost" not real bill. Real bill needs per-org plan-type
  config (Pro/Max/Team/API). Optionally: connect Anthropic Admin API for
  exact billed usage.
- [ ] **Cursor + Copilot pricing** — same as-if-API treatment as Claude. If
  you want real Cursor billing, integrate with their usage API
  (`usageUuid` on each composer).
- [ ] **`<synthetic>` model fallback** — Claude Code CLI sometimes emits
  `model: "<synthetic>"` for non-API turns. We fall back to $5/Mtok blended.
  Verify whether these turns should be counted at all (they may be local-only
  with no real cost).

## UI debt — known rough edges

- [ ] **Custom login page** — Cognito Hosted UI is the default red-on-white
  AWS look and feels off-brand. Replace with our own form using direct
  Cognito InitiateAuth + the user pool's USER_PASSWORD_AUTH flow (or
  AWS Amplify Auth). Covers: signin, signup, email verify, MFA, password
  reset. Estimated 4–6 hours. Until then, the Hosted UI works but looks
  poor.
- [ ] **Cognito Hosted UI CSS customization** — quick stopgap: upload
  dark-theme CSS + VibeROI logo via `aws_cognito_user_pool_ui_customization`
  terraform resource. Limited (Cognito allows ~30 selectors only) but
  goes from default-AWS to branded in ~30 min.

## After deploy

These need redoing once the API + frontend are on a real URL:

- [ ] Update Cognito callback URLs in Terraform (`infra/terraform/envs/dev/main.tf`
  `callback_urls`) to include the deployed domain.
- [ ] Update `frontend/.env` `VITE_COGNITO_REDIRECT_URI` to the deployed
  domain.
- [ ] Move dev `.env.local` secrets to AWS Secrets Manager via the
  `viberoi_shared.secrets` wrapper.

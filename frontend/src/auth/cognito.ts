/**
 * Cognito Hosted UI + PKCE flow — hand-rolled, no SDK.
 *
 * Hosted UI handles signup, signin, MFA, password reset. We just:
 *   1. Generate a PKCE verifier/challenge, store verifier in sessionStorage.
 *   2. Redirect to Hosted UI /authorize with the challenge.
 *   3. Hosted UI redirects back to /auth/callback?code=XXX&state=YYY.
 *   4. Exchange code + verifier for tokens at /oauth2/token.
 *   5. Store access_token in memory + sessionStorage (NOT localStorage).
 *
 * Logout: redirect to /logout?client_id=...&logout_uri=... — Cognito
 * clears its session cookie then redirects back.
 */

const DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN as string;
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID as string;
const REDIRECT_URI = import.meta.env.VITE_COGNITO_REDIRECT_URI as string;
const LOGOUT_URI = import.meta.env.VITE_COGNITO_LOGOUT_URI as string;
const SCOPE = "openid email profile";

const PKCE_VERIFIER_KEY = "viberoi.pkce_verifier";
const PKCE_STATE_KEY = "viberoi.pkce_state";

export const cognitoConfigured = Boolean(DOMAIN && CLIENT_ID && REDIRECT_URI);

export interface CognitoSession {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresAt: number; // epoch ms
  sub: string;
  email: string;
}

const SESSION_KEY = "viberoi.cognito_session";

export function readSession(): CognitoSession | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as CognitoSession;
    if (s.expiresAt < Date.now() + 10_000) return null; // 10s grace
    return s;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

function persistSession(s: CognitoSession): void {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
}

// ── PKCE helpers ───────────────────────────────────────────────────────────

function randomString(bytes: number): string {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return Array.from(arr, (b) => b.toString(16).padStart(2, "0")).join("");
}

async function sha256Base64Url(input: string): Promise<string> {
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(input),
  );
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

// ── Login + logout redirects ───────────────────────────────────────────────

export async function startLogin(): Promise<void> {
  if (!cognitoConfigured) {
    throw new Error("Cognito env vars not set — see frontend/.env");
  }
  const verifier = randomString(32);
  const state = randomString(16);
  const challenge = await sha256Base64Url(verifier);
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(PKCE_STATE_KEY, state);

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    scope: SCOPE,
    redirect_uri: REDIRECT_URI,
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  window.location.assign(`https://${DOMAIN}/oauth2/authorize?${params}`);
}

export function startLogout(): void {
  clearSession();
  if (!cognitoConfigured) {
    window.location.assign("/");
    return;
  }
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    logout_uri: LOGOUT_URI,
  });
  window.location.assign(`https://${DOMAIN}/logout?${params}`);
}

// ── Callback handler ───────────────────────────────────────────────────────

export async function completeLogin(
  code: string,
  state: string,
): Promise<CognitoSession> {
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  const expectedState = sessionStorage.getItem(PKCE_STATE_KEY);
  if (!verifier) throw new Error("PKCE verifier missing — start login again.");
  if (state !== expectedState) throw new Error("OAuth state mismatch.");
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  sessionStorage.removeItem(PKCE_STATE_KEY);

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: CLIENT_ID,
    code,
    redirect_uri: REDIRECT_URI,
    code_verifier: verifier,
  });
  const resp = await fetch(`https://${DOMAIN}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!resp.ok) {
    throw new Error(`Token exchange failed: ${resp.status} ${await resp.text()}`);
  }
  const tokens = (await resp.json()) as {
    access_token: string;
    id_token: string;
    refresh_token: string;
    expires_in: number;
    token_type: string;
  };

  const idClaims = parseJwtClaims(tokens.id_token);
  const session: CognitoSession = {
    accessToken: tokens.access_token,
    idToken: tokens.id_token,
    refreshToken: tokens.refresh_token,
    expiresAt: Date.now() + tokens.expires_in * 1000,
    sub: idClaims.sub,
    email: idClaims.email ?? "(unknown)",
  };
  persistSession(session);
  return session;
}

function parseJwtClaims(token: string): { sub: string; email?: string } {
  // No signature verification — backend does that. We only need claims
  // for display (email shown in sidebar).
  const [, payload] = token.split(".");
  const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
  return JSON.parse(decoded) as { sub: string; email?: string };
}

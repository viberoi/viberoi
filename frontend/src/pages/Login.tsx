/**
 * Login — two paths:
 *   - "Sign in with Cognito" → Hosted UI (signup, signin, MFA, reset)
 *   - "Dev mode" expander → hardcoded user picker (local testing only)
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronRight, Zap } from "lucide-react";

import { type AuthUser, type Role, useAuth } from "../auth/AuthContext";
import { cognitoConfigured, startLogin } from "../auth/cognito";

const DEV_ORG_ID = "00000000-0000-0000-0000-000000000001";
const DEV_TEAM_ID = "00000000-0000-0000-0000-000000000010";

const DEV_USERS: Omit<AuthUser, "source">[] = [
  {
    email: "admin@acme.test",
    developerId: "00000000-0000-0000-0000-000000000101",
    orgId: DEV_ORG_ID,
    role: "OrgAdmin" as Role,
    teamId: null,
  },
  {
    email: "lead@acme.test",
    developerId: "00000000-0000-0000-0000-000000000102",
    orgId: DEV_ORG_ID,
    role: "TeamLead" as Role,
    teamId: DEV_TEAM_ID,
  },
  {
    email: "dev@acme.test",
    developerId: "00000000-0000-0000-0000-000000000103",
    orgId: DEV_ORG_ID,
    role: "Developer" as Role,
    teamId: DEV_TEAM_ID,
  },
];

export function Login() {
  const { setDevUser } = useAuth();
  const navigate = useNavigate();
  const [devOpen, setDevOpen] = useState(false);
  const [signingIn, setSigningIn] = useState(false);

  return (
    <div className="min-h-screen flex items-center justify-center bg-viberoi-bg">
      <div className="w-96 bg-viberoi-card border border-white/5 rounded-xl p-8">
        <div className="flex items-center gap-2 mb-8">
          <div className="w-9 h-9 rounded-md bg-viberoi-accent/10 border border-viberoi-accent/30 flex items-center justify-center">
            <Zap size={18} className="text-viberoi-accent" />
          </div>
          <span className="font-ui font-bold text-lg tracking-tight">
            VibeROI
          </span>
        </div>
        <div className="font-ui text-xl font-bold mb-1">Sign in</div>
        <div className="text-sm text-viberoi-sub mb-6">
          Privacy-first AI engineering ROI.
        </div>

        <button
          onClick={() => {
            setSigningIn(true);
            void startLogin().catch((e: Error) => {
              setSigningIn(false);
              alert(e.message);
            });
          }}
          disabled={!cognitoConfigured || signingIn}
          className="w-full px-4 py-3 rounded-md bg-viberoi-accent text-black font-semibold hover:bg-viberoi-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {signingIn ? "Redirecting…" : "Sign in / Sign up"}
        </button>
        {!cognitoConfigured && (
          <div className="mt-2 text-xs text-red-300">
            Cognito env vars not set — see frontend/.env
          </div>
        )}

        <button
          onClick={() => setDevOpen(!devOpen)}
          className="mt-6 w-full flex items-center gap-1 text-xs uppercase tracking-wider text-viberoi-sub hover:text-viberoi-text"
        >
          {devOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          Dev mode (local only)
        </button>
        {devOpen && (
          <ul className="space-y-2 mt-3">
            {DEV_USERS.map((u) => (
              <li key={u.email}>
                <button
                  onClick={() => {
                    setDevUser(u);
                    navigate("/dashboard");
                  }}
                  className="w-full text-left flex items-center justify-between gap-2 px-3 py-2 rounded-md bg-viberoi-surface hover:bg-white/5 border border-transparent hover:border-viberoi-accent/30 transition-colors text-sm"
                >
                  <span>
                    <div>{u.email}</div>
                    <div className="text-[10px] uppercase tracking-wider text-viberoi-sub">
                      {u.role}
                    </div>
                  </span>
                  <span className="text-viberoi-accent text-xs">→</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

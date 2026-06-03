/**
 * Dev-mode login.
 *
 * Picks from a few hardcoded users so we can exercise each RBAC bucket
 * without provisioning Cognito. The users mirror what the seed script
 * (`scripts/seed-dev-data.py`) inserts so the API has matching rows.
 *
 * When real Cognito lands this entire file becomes the OAuth callback
 * handler; the rest of the app (which reads `useAuth().user`) doesn't
 * change.
 */

import { useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";

import { type DevUser, type Role, useAuth } from "../auth/AuthContext";

const DEV_ORG_ID = "00000000-0000-0000-0000-000000000001";
const DEV_TEAM_ID = "00000000-0000-0000-0000-000000000010";

const DEV_USERS: DevUser[] = [
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
  const { setUser } = useAuth();
  const navigate = useNavigate();

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
          <span className="ml-auto text-[10px] uppercase tracking-widest bg-white/5 text-viberoi-sub px-2 py-1 rounded">
            dev
          </span>
        </div>
        <div className="font-ui text-xl font-bold mb-1">Pick a dev user</div>
        <div className="text-sm text-viberoi-sub mb-6">
          Cognito hosted UI replaces this in Slice 6.
        </div>
        <ul className="space-y-2">
          {DEV_USERS.map((u) => (
            <li key={u.email}>
              <button
                onClick={() => {
                  setUser(u);
                  navigate("/dashboard");
                }}
                className="w-full text-left flex items-center justify-between gap-2 px-4 py-3 rounded-md bg-viberoi-surface hover:bg-white/5 border border-transparent hover:border-viberoi-accent/30 transition-colors"
              >
                <span>
                  <div className="text-sm">{u.email}</div>
                  <div className="text-[11px] uppercase tracking-wider text-viberoi-sub">
                    {u.role}
                    {u.teamId ? " · team-A" : ""}
                  </div>
                </span>
                <span className="text-viberoi-accent text-xs">Sign in →</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

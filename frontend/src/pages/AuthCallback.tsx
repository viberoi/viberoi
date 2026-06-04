import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { completeLogin } from "../auth/cognito";

export function AuthCallback() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { setCognitoUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  // Guard against React StrictMode double-fire — the PKCE verifier and
  // OAuth code are single-use; running completeLogin twice would error.
  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;
    const code = params.get("code");
    const state = params.get("state");
    const err = params.get("error");
    if (err) {
      setError(`${err}: ${params.get("error_description") ?? ""}`);
      return;
    }
    if (!code || !state) {
      setError("missing code/state in callback URL");
      return;
    }
    completeLogin(code, state)
      .then(async (session) => {
        // Fetch /developers/me with the new token to populate the user profile.
        const resp = await fetch("/api/developers/me", {
          headers: {
            Authorization: `Bearer ${session.accessToken}`,
            Accept: "application/json",
          },
        });
        if (resp.status === 401) {
          setError(
            "Cognito sign-in succeeded but no developer record found in the local DB. " +
              `Run: uv run python scripts/bootstrap-cognito-user.py --email ${session.email} --sub ${session.sub}`,
          );
          return;
        }
        if (!resp.ok) {
          setError(`/developers/me ${resp.status}`);
          return;
        }
        const body = (await resp.json()) as {
          developer_id: string;
          org_id: string;
          role: "OrgAdmin" | "TeamLead" | "Developer";
          team_id: string | null;
          email: string;
        };
        setCognitoUser(session, {
          email: body.email,
          developerId: body.developer_id,
          orgId: body.org_id,
          role: body.role,
          teamId: body.team_id,
          source: "cognito",
        });
        nav("/dashboard", { replace: true });
      })
      .catch((e: Error) => setError(e.message));
  }, [params, nav, setCognitoUser]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-viberoi-bg p-6">
        <div className="max-w-xl bg-red-500/10 border border-red-500/30 rounded-lg p-6">
          <div className="font-ui font-semibold text-red-300 mb-2">
            Sign-in failed
          </div>
          <div className="text-sm font-mono whitespace-pre-wrap text-red-200">
            {error}
          </div>
          <button
            onClick={() => nav("/login")}
            className="mt-4 text-sm text-viberoi-accent hover:underline"
          >
            ← back to login
          </button>
        </div>
      </div>
    );
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-viberoi-bg">
      <div className="flex items-center gap-2 text-viberoi-sub">
        <Loader2 size={16} className="animate-spin" />
        <span>Completing sign-in…</span>
      </div>
    </div>
  );
}

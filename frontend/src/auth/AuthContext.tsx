/**
 * Auth state — supports two modes:
 *   - Dev: hardcoded user picker → identity in X-Dev-* headers (gated to env=dev on server)
 *   - Cognito: real Hosted UI signin → Bearer <access_token>
 *
 * Both modes expose `user` with the same shape so pages don't branch.
 * When Cognito is in use, `developerId/orgId/role/teamId` come from the
 * /developers/me response (resolved server-side via cognito_sub).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  type CognitoSession,
  clearSession,
  readSession,
  startLogout,
} from "./cognito";

export type Role = "OrgAdmin" | "TeamLead" | "Developer";

export interface AuthUser {
  email: string;
  developerId: string;
  orgId: string;
  role: Role;
  teamId: string | null;
  source: "dev" | "cognito";
}

const DEV_STORAGE_KEY = "viberoi.dev_user";

function readStoredDevUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(DEV_STORAGE_KEY);
    if (!raw) return null;
    const stored = JSON.parse(raw) as Omit<AuthUser, "source">;
    return { ...stored, source: "dev" };
  } catch {
    return null;
  }
}

interface AuthCtx {
  user: AuthUser | null;
  cognitoSession: CognitoSession | null;
  setDevUser: (u: Omit<AuthUser, "source">) => void;
  setCognitoUser: (session: CognitoSession, user: AuthUser) => void;
  logout: () => void;
}

const Context = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<AuthUser | null>(() =>
    readStoredDevUser(),
  );
  const [cognitoSession, setCognitoSessionState] =
    useState<CognitoSession | null>(() => readSession());

  // If a Cognito session is in sessionStorage but we don't have a user
  // profile yet (e.g. page reload after login), fetch /developers/me.
  useEffect(() => {
    if (cognitoSession && (!user || user.source !== "cognito")) {
      void fetchSelfAndPopulate(cognitoSession).then((u) => {
        if (u) setUserState(u);
      });
    }
  }, [cognitoSession, user]);

  const setDevUser = useCallback((u: Omit<AuthUser, "source">) => {
    localStorage.setItem(DEV_STORAGE_KEY, JSON.stringify(u));
    clearSession();
    setCognitoSessionState(null);
    setUserState({ ...u, source: "dev" });
  }, []);

  const setCognitoUser = useCallback(
    (session: CognitoSession, u: AuthUser) => {
      localStorage.removeItem(DEV_STORAGE_KEY);
      setCognitoSessionState(session);
      setUserState(u);
    },
    [],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(DEV_STORAGE_KEY);
    setUserState(null);
    if (cognitoSession) {
      startLogout(); // redirects to Cognito then back
    } else {
      window.location.assign("/login");
    }
  }, [cognitoSession]);

  const value = useMemo<AuthCtx>(
    () => ({ user, cognitoSession, setDevUser, setCognitoUser, logout }),
    [user, cognitoSession, setDevUser, setCognitoUser, logout],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Context);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

async function fetchSelfAndPopulate(
  session: CognitoSession,
): Promise<AuthUser | null> {
  // Use raw fetch (api/client.ts would import this module and loop).
  try {
    const resp = await fetch("/api/developers/me", {
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
        Accept: "application/json",
      },
    });
    if (!resp.ok) {
      console.warn(`/developers/me failed: ${resp.status}`);
      return null;
    }
    const body = (await resp.json()) as {
      developer_id: string;
      org_id: string;
      role: Role;
      team_id: string | null;
      email: string;
    };
    return {
      email: body.email,
      developerId: body.developer_id,
      orgId: body.org_id,
      role: body.role,
      teamId: body.team_id,
      source: "cognito",
    };
  } catch (e) {
    console.warn("fetchSelf failed", e);
    return null;
  }
}

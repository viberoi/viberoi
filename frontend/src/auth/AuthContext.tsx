/**
 * Dev-mode auth.
 *
 * Until real Cognito is provisioned (Slice 6 — infra batch), the frontend
 * picks one of a few hardcoded "dev users" from a list and stores their
 * identity in `localStorage`. Every API call carries the user's identity
 * via custom headers (`X-Dev-*`), and the API service accepts those
 * headers ONLY when `env=dev`. The real Cognito JWT path is untouched.
 *
 * When Cognito lands, the storage shape stays the same — the only thing
 * that changes is where `setUser` gets the values from (a real access
 * token instead of a hardcoded pick).
 */

import { createContext, useCallback, useContext, useMemo, useState } from "react";

export type Role = "OrgAdmin" | "TeamLead" | "Developer";

export interface DevUser {
  email: string;
  developerId: string;
  orgId: string;
  role: Role;
  teamId: string | null;
}

const STORAGE_KEY = "viberoi.dev_user";

function readStoredUser(): DevUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as DevUser;
  } catch {
    return null;
  }
}

interface AuthCtx {
  user: DevUser | null;
  setUser: (u: DevUser) => void;
  logout: () => void;
}

const Context = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<DevUser | null>(() => readStoredUser());

  const setUser = useCallback((u: DevUser) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    setUserState(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUserState(null);
  }, []);

  const value = useMemo<AuthCtx>(() => ({ user, setUser, logout }), [user, setUser, logout]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Context);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

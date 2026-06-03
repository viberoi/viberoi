/**
 * Typed fetch wrapper.
 *
 * Reads the dev-mode user from localStorage and attaches the `X-Dev-*`
 * headers the API service expects. When real Cognito lands the headers
 * will become a single `Authorization: Bearer <access_token>`; the rest
 * of this module won't need to change.
 */

const STORAGE_KEY = "viberoi.dev_user";

interface DevUser {
  email: string;
  developerId: string;
  orgId: string;
  role: string;
  teamId: string | null;
}

function readUser(): DevUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as DevUser) : null;
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly path: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const user = readUser();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (user) {
    headers["X-Dev-Developer-Id"] = user.developerId;
    headers["X-Dev-Org-Id"] = user.orgId;
    headers["X-Dev-Role"] = user.role;
    if (user.teamId) headers["X-Dev-Team-Id"] = user.teamId;
  }

  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(response.status, path, detail);
  }
  return (await response.json()) as T;
}

// ── Typed endpoints ───────────────────────────────────────────────────────

export interface KpiSnapshot {
  window_days: number;
  total_sessions: number;
  total_tokens: number;
  total_cost_usd: string;
  active_developers: number;
  avg_session_duration_seconds: number | null;
  hallucination_loop_rate: number | null;
}

export interface SessionSummary {
  id: string;
  external_id: string;
  developer_id: string;
  tool_name: string;
  model: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  total_tokens: number;
  cost_usd: string;
  ticket_external_id: string | null;
  sprint_id: string | null;
  branch_name: string | null;
  schema_version: string;
}

export interface SessionListResponse {
  items: SessionSummary[];
  next_cursor: string | null;
}

export const api = {
  kpiSnapshot: (windowDays = 30) =>
    request<KpiSnapshot>(`/kpis/snapshot?window_days=${windowDays}`),
  listSessions: (cursor?: string, limit = 50) => {
    const q = new URLSearchParams();
    if (cursor) q.set("cursor", cursor);
    q.set("limit", String(limit));
    return request<SessionListResponse>(`/sessions?${q.toString()}`);
  },
};

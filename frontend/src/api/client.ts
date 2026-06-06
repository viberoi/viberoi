/**
 * Typed fetch wrapper.
 *
 * Reads the dev-mode user from localStorage and attaches the `X-Dev-*`
 * headers the API service expects. When real Cognito lands the headers
 * will become a single `Authorization: Bearer <access_token>`; the rest
 * of this module won't need to change.
 */

import { readSession } from "../auth/cognito";

const DEV_STORAGE_KEY = "viberoi.dev_user";

interface DevUser {
  email: string;
  developerId: string;
  orgId: string;
  role: string;
  teamId: string | null;
}

function readDevUser(): DevUser | null {
  try {
    const raw = localStorage.getItem(DEV_STORAGE_KEY);
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
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.headers as Record<string, string>),
  };
  // Prefer Cognito Bearer when present; fall back to X-Dev-* headers.
  const session = readSession();
  if (session) {
    headers["Authorization"] = `Bearer ${session.accessToken}`;
  } else {
    const user = readDevUser();
    if (user) {
      headers["X-Dev-Developer-Id"] = user.developerId;
      headers["X-Dev-Org-Id"] = user.orgId;
      headers["X-Dev-Role"] = user.role;
      if (user.teamId) headers["X-Dev-Team-Id"] = user.teamId;
    }
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
  if (response.status === 204) return undefined as T;
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

export interface SessionDetail extends SessionSummary {
  tokens_input: number;
  tokens_output: number;
  tokens_cache_read: number;
  tokens_cache_write: number;
  is_estimated: boolean;
  turn_count: number;
  subagent_count: number;
  mode: string;
  is_agentic: boolean;
  lines_added: number;
  lines_deleted: number;
  is_committed: boolean;
  commit_count: number;
  session_restarts: number | null;
  file_oscillations: number | null;
  attribution_signals: string[];
  attribution_confidence: number | null;
  attribution_method: string | null;
  files_touched_count: number;
  files_touched: string[];
  repo_name: string | null;
  repo_cwd: string | null;
}

export interface SprintSummary {
  id: string;
  system: string;
  external_id: string;
  name: string;
  state: string;
  started_at: string | null;
  ended_at: string | null;
  completed_at: string | null;
  board_id: string | null;
  ticket_count: number;
}

export interface SprintListResponse {
  items: SprintSummary[];
}

export interface SprintDetail extends SprintSummary {
  total_cost_usd: string;
  total_sessions: number;
}

export interface TicketDetail {
  id: string;
  system: string;
  external_id: string;
  title: string;
  status: string;
  sprint_id: string | null;
  assignee_developer_id: string | null;
  story_points: string | null;
  priority: string | null;
  created_at_external: string;
  closed_at_external: string | null;
  total_sessions: number;
  total_cost_usd: string;
}

export interface DeveloperProfile {
  id: string;
  org_id: string;
  role: string;
  team_id: string | null;
  email: string;
  github_username: string | null;
  agent_status: string;
  created_at: string;
  last_active_at: string | null;
}

// ── Integrations (Integration service) ─────────────────────────────────────

export interface IntegrationSummary {
  id: string;
  provider: string;
  installed_by_developer_id: string | null;
  expires_at: string | null;
  scope: string | null;
  created_at: string;
  webhook_registration_status: string | null;
  last_sync_at: string | null;
  revoked: boolean;
}

export interface ConnectResponse {
  authorize_url: string;
}

export interface SyncEnqueuedResponse {
  sync_type: string;
  enqueued: boolean;
  trace_id: string;
}

// ── Notification channels ──────────────────────────────────────────────────

export interface NotificationChannelSummary {
  id: string;
  channel: string;
  has_webhook_url: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationChannelListResponse {
  items: NotificationChannelSummary[];
}

export const api = {
  kpiSnapshot: (windowDays = 30) =>
    request<KpiSnapshot>(`/kpis/snapshot?window_days=${windowDays}`),

  kpiTimeseries: (windowDays = 30) =>
    request<TimeseriesResponse>(`/kpis/timeseries?window_days=${windowDays}`),

  kpiByDeveloper: (windowDays = 30, limit = 10) =>
    request<ByDeveloperResponse>(
      `/kpis/by-developer?window_days=${windowDays}&limit=${limit}`,
    ),

  kpiByTool: (windowDays = 30) =>
    request<ByToolResponse>(`/kpis/by-tool?window_days=${windowDays}`),

  kpiByModel: (windowDays = 30) =>
    request<ByModelResponse>(`/kpis/by-model?window_days=${windowDays}`),

  kpiByMode: (windowDays = 30) =>
    request<ByModeResponse>(`/kpis/by-mode?window_days=${windowDays}`),

  kpiPerTicket: (windowDays = 30, limit = 10) =>
    request<PerTicketResponse>(
      `/kpis/per-ticket?window_days=${windowDays}&limit=${limit}`,
    ),

  // ── /me/* — caller's personal data only ──────────────────────────────────
  mySessions: (cursor?: string, limit = 50) => {
    const q = new URLSearchParams();
    if (cursor) q.set("cursor", cursor);
    q.set("limit", String(limit));
    return request<SessionListResponse>(`/me/sessions?${q.toString()}`);
  },

  mySummary: (windowDays = 30) =>
    request<MeSummary>(`/me/summary?window_days=${windowDays}`),

  listSessions: (cursor?: string, limit = 50) => {
    const q = new URLSearchParams();
    if (cursor) q.set("cursor", cursor);
    q.set("limit", String(limit));
    return request<SessionListResponse>(`/sessions?${q.toString()}`);
  },

  getSession: (id: string) => request<SessionDetail>(`/sessions/${id}`),

  // Sprint state filter is repeated for each value Cognito-quoted URLs.
  listSprints: (states?: string[]) => {
    const q = new URLSearchParams();
    states?.forEach((s) => q.append("state", s));
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return request<SprintListResponse>(`/sprints${suffix}`);
  },

  getSprint: (id: string) => request<SprintDetail>(`/sprints/${id}`),

  getTicket: (id: string) => request<TicketDetail>(`/tickets/${id}`),

  listTicketsInSprint: (sprintId: string) =>
    request<{ items: TicketDetail[] }>(`/sprints/${sprintId}/tickets`),

  listSessionsForTicket: (ticketId: string) =>
    request<SessionListResponse>(`/tickets/${ticketId}/sessions`),

  me: () => request<DeveloperProfile>(`/developers/me`),

  // ── Integrations (Integration service — different base) ────────────────
  // The frontend's /api proxy points at the API service. The Integration
  // service runs separately; for dev, we go through the same proxy. In
  // production both are fronted by the same ALB with path-based routing.
  listIntegrations: () =>
    request<IntegrationSummary[]>(`/integrations`),

  connectIntegration: (provider: string) =>
    request<ConnectResponse>(`/integrations/${provider}/connect`, {
      method: "POST",
    }),

  disconnectIntegration: (provider: string) =>
    request<void>(`/integrations/${provider}`, { method: "DELETE" }),

  syncIntegration: (provider: string) =>
    request<SyncEnqueuedResponse>(`/integrations/${provider}/sync`, {
      method: "POST",
    }),

  // ── Notification channels ────────────────────────────────────────────────
  listChannels: () =>
    request<NotificationChannelListResponse>(`/notifications/channels`),

  upsertChannel: (channel: string, webhookUrl: string) =>
    request<NotificationChannelSummary>(`/notifications/channels`, {
      method: "POST",
      body: JSON.stringify({ channel, webhook_url: webhookUrl }),
      headers: { "Content-Type": "application/json" },
    }),

  disableChannel: (channel: string) =>
    request<void>(`/notifications/channels/${channel}`, { method: "DELETE" }),

  // ── Team invites ─────────────────────────────────────────────────────────
  inviteTeammate: (email: string) =>
    request<InviteResponse>(`/invitations`, {
      method: "POST",
      body: JSON.stringify({ email }),
      headers: { "Content-Type": "application/json" },
    }),
};

export interface InviteResponse {
  developer_id: string;
  email: string;
  role: string;
  cognito_sub: string;
  message: string;
}

export interface TimeseriesPoint {
  day: string;
  sessions: number;
  tokens: number;
  cost_usd: string;
}

export interface TimeseriesResponse {
  window_days: number;
  points: TimeseriesPoint[];
}

export interface DeveloperRollup {
  developer_id: string;
  email: string;
  role: string;
  sessions: number;
  tokens: number;
  cost_usd: string;
  lines_added: number;
  lines_deleted: number;
  commit_count: number;
}

export interface ByDeveloperResponse {
  window_days: number;
  items: DeveloperRollup[];
}

export interface ToolRollup {
  tool_name: string;
  sessions: number;
  tokens: number;
  cost_usd: string;
}

export interface ByToolResponse {
  window_days: number;
  items: ToolRollup[];
}

export interface ModelRollup {
  model: string;
  sessions: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: string;
}

export interface ByModelResponse {
  window_days: number;
  items: ModelRollup[];
}

export interface ModeRollup {
  mode: string;
  sessions: number;
  cost_usd: string;
}

export interface ByModeResponse {
  window_days: number;
  items: ModeRollup[];
}

export interface TicketRollup {
  ticket_external_id: string;
  sessions: number;
  tokens: number;
  cost_usd: string;
}

export interface PerTicketResponse {
  window_days: number;
  items: TicketRollup[];
}

export interface MeSummary {
  window_days: number;
  sessions: number;
  tokens: number;
  cost_usd: string;
  lines_added: number;
  lines_deleted: number;
  commit_count: number;
  avg_session_duration_seconds: number | null;
  last_session_at: string | null;
  tool_mix: Array<{ tool_name: string; sessions: number; cost_usd: string }>;
  model_mix: Array<{ model: string; sessions: number; cost_usd: string }>;
  mode_mix: Array<{ mode: string; sessions: number }>;
  top_tickets: Array<{
    ticket_external_id: string;
    sessions: number;
    cost_usd: string;
  }>;
}

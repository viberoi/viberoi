/**
 * S-04 Developer Profiles (People)
 * List view + slide-in detail panel per developer.
 * 
 * REAL API CONTRACTS (replace mock with these in build):
 *   List: GET /api/v1/people?sprint_id=SPRINT-42&team_id=all
 *   Detail: GET /api/v1/people/:developer_id
 * 
 * Mock data shapes exactly match real API response.
 * Coding agent: swap MOCK_PEOPLE with api.get('/people')
 */

import { useState } from "react";
import {
  X, ChevronDown, Download, ArrowUpRight, ArrowDownRight,
  GitCommit, Clock, Zap, FileCode, BarChart2, ChevronRight,
  AlertTriangle, CheckCircle,
} from "lucide-react";

/* ─── Design Tokens ──────────────────────────────────────── */
const C = {
  bg: "#080808", card: "#101010", surface: "#181818",
  hover: "#1E1E1E", accent: "#00D4FF", accentBg: "rgba(0,212,255,0.08)",
  warm: "#FFB547", warmBg: "rgba(255,181,71,0.08)",
  green: "#00E676", greenBg: "rgba(0,230,118,0.08)",
  red: "#FF4545", redBg: "rgba(255,69,69,0.08)",
  amber: "#FFB800", amberBg: "rgba(255,184,0,0.08)",
  purple: "#A78BFA", purpleBg: "rgba(167,139,250,0.08)",
  text: "#F0F0F0", sub: "#5A5A5A", muted: "#2E2E2E",
  border: "rgba(255,255,255,0.07)", borderHi: "rgba(255,255,255,0.14)",
} as const;

const F = {
  ui: "'Outfit', sans-serif",
  body: "'DM Sans', sans-serif",
  mono: "'JetBrains Mono', monospace",
};

/* ─── Mock Data (matches real API shape exactly) ─────────── */
// GET /api/v1/people?sprint_id=SPRINT-42
const MOCK_PEOPLE = [
  {
    developer_id: "dev_adnan_123",
    name: "Adnan K", email: "adnan@company.com",
    role: "team_lead", primary_tool: "Claude Code",
    avatar_initials: "AK", avatar_color: C.accent,
    sprint: {
      ai_spend_usd: 142, tickets_closed: 8,
      cost_per_ticket: 17.75, sessions: 18, ai_code_pct: 84,
      efficiency_score: 78, pr_size_avg: 980,
      commits_7d: [3, 5, 4, 6, 5, 1, 0],
      lines_added: 3240, lines_deleted: 820, lines_accepted: 2724,
      mode_breakdown: { agent: 62, chat: 18, edit: 12, plan: 8 },
      tokens_in: 142400, tokens_out: 268600,
    },
    agent_status: "active", last_session_at: "2026-05-28T14:32:00Z",
    sessions: [
      { session_id: "s1", started_at: "2026-05-28T09:28:35Z", tool: "claude-code", model: "claude-sonnet-4-6", active_duration_min: 74, total_cost_usd: 0.42, is_estimated: false, attribution: { ticket_id: "JIRA-142", confidence: 0.87, method: "branch_parse" }, hallucination_risk: "none", is_committed: true, lines_added: 47, lines_accepted: 38 },
      { session_id: "s2", started_at: "2026-05-27T14:15:00Z", tool: "claude-code", model: "claude-sonnet-4-6", active_duration_min: 92, total_cost_usd: 0.68, is_estimated: false, attribution: { ticket_id: "JIRA-142", confidence: 0.87, method: "branch_parse" }, hallucination_risk: "watch", is_committed: true, lines_added: 82, lines_accepted: 61 },
      { session_id: "s3", started_at: "2026-05-27T10:00:00Z", tool: "cursor", model: "gpt-4o", active_duration_min: 45, total_cost_usd: 1.20, is_estimated: false, attribution: { ticket_id: "JIRA-155", confidence: 0.92, method: "branch_parse" }, hallucination_risk: "none", is_committed: true, lines_added: 34, lines_accepted: 29 },
    ],
    commit_breakdown: [
      { tool: "Claude Code", commits: 35, accepted_lines: 24473, repos: ["wvp-backend", "auth-service"] },
      { tool: "Cursor", commits: 1, accepted_lines: 904, repos: ["wvp-backend"] },
    ],
  },
  {
    developer_id: "dev_sara_124",
    name: "Sara P", email: "sara@company.com",
    role: "developer", primary_tool: "Cursor",
    avatar_initials: "SP", avatar_color: C.purple,
    sprint: {
      ai_spend_usd: 98, tickets_closed: 6,
      cost_per_ticket: 16.33, sessions: 14, ai_code_pct: 71,
      efficiency_score: 82, pr_size_avg: 2100,
      commits_7d: [2, 4, 3, 5, 4, 0, 0],
      lines_added: 2180, lines_deleted: 640, lines_accepted: 1548,
      mode_breakdown: { agent: 71, chat: 14, edit: 10, plan: 5 },
      tokens_in: 98200, tokens_out: 184100,
    },
    agent_status: "active", last_session_at: "2026-05-28T11:15:00Z",
    sessions: [
      { session_id: "s4", started_at: "2026-05-28T11:00:00Z", tool: "cursor", model: "claude-sonnet-4-6", active_duration_min: 45, total_cost_usd: 1.20, is_estimated: false, attribution: { ticket_id: "JIRA-151", confidence: 0.71, method: "branch_parse" }, hallucination_risk: "alert", is_committed: false, lines_added: 180, lines_accepted: 0 },
    ],
    commit_breakdown: [
      { tool: "Cursor", commits: 14, accepted_lines: 8920, repos: ["wvp-backend"] },
    ],
  },
  {
    developer_id: "dev_raj_125",
    name: "Raj K", email: "raj@company.com",
    role: "developer", primary_tool: "Claude Code",
    avatar_initials: "RK", avatar_color: C.green,
    sprint: {
      ai_spend_usd: 67, tickets_closed: 7,
      cost_per_ticket: 9.57, sessions: 9, ai_code_pct: 88,
      efficiency_score: 91, pr_size_avg: 720,
      commits_7d: [4, 6, 5, 7, 5, 2, 1],
      lines_added: 1840, lines_deleted: 320, lines_accepted: 1619,
      mode_breakdown: { agent: 55, chat: 22, edit: 14, plan: 9 },
      tokens_in: 67000, tokens_out: 124800,
    },
    agent_status: "active", last_session_at: "2026-05-28T16:00:00Z",
    sessions: [],
    commit_breakdown: [
      { tool: "Claude Code", commits: 28, accepted_lines: 14200, repos: ["payment-service"] },
    ],
  },
  {
    developer_id: "dev_priya_126",
    name: "Priya M", email: "priya@company.com",
    role: "developer", primary_tool: "Copilot",
    avatar_initials: "PM", avatar_color: C.warm,
    sprint: {
      ai_spend_usd: 53, tickets_closed: 5,
      cost_per_ticket: 10.60, sessions: 8, ai_code_pct: 76,
      efficiency_score: 74, pr_size_avg: 850,
      commits_7d: [2, 3, 4, 4, 3, 0, 0],
      lines_added: 1240, lines_deleted: 280, lines_accepted: 943,
      mode_breakdown: { agent: 0, chat: 78, edit: 22, plan: 0 },
      tokens_in: 53000, tokens_out: 98400,
    },
    agent_status: "active", last_session_at: "2026-05-27T17:30:00Z",
    sessions: [],
    commit_breakdown: [
      { tool: "Copilot", commits: 12, accepted_lines: 7840, repos: ["frontend-web"] },
    ],
  },
  {
    developer_id: "dev_vikram_127",
    name: "Vikram S", email: "vikram@company.com",
    role: "developer", primary_tool: "Cursor",
    avatar_initials: "VS", avatar_color: C.amber,
    sprint: {
      ai_spend_usd: 38, tickets_closed: 4,
      cost_per_ticket: 9.50, sessions: 6, ai_code_pct: 69,
      efficiency_score: 68, pr_size_avg: 1100,
      commits_7d: [1, 2, 2, 3, 2, 0, 0],
      lines_added: 890, lines_deleted: 210, lines_accepted: 614,
      mode_breakdown: { agent: 48, chat: 30, edit: 14, plan: 8 },
      tokens_in: 38000, tokens_out: 72000,
    },
    agent_status: "active", last_session_at: "2026-05-28T10:00:00Z",
    sessions: [],
    commit_breakdown: [
      { tool: "Cursor", commits: 8, accepted_lines: 4820, repos: ["wvp-backend"] },
    ],
  },
  {
    developer_id: "dev_meera_128",
    name: "Meera T", email: "meera@company.com",
    role: "developer", primary_tool: "Cursor",
    avatar_initials: "MT", avatar_color: C.sub,
    sprint: {
      ai_spend_usd: 12, tickets_closed: 2,
      cost_per_ticket: 6.00, sessions: 3, ai_code_pct: 45,
      efficiency_score: 55, pr_size_avg: 430,
      commits_7d: [0, 1, 1, 2, 1, 0, 0],
      lines_added: 320, lines_deleted: 80, lines_accepted: 144,
      mode_breakdown: { agent: 0, chat: 90, edit: 10, plan: 0 },
      tokens_in: 12000, tokens_out: 22400,
    },
    agent_status: "inactive", last_session_at: "2026-05-25T09:00:00Z",
    sessions: [],
    commit_breakdown: [
      { tool: "Cursor", commits: 3, accepted_lines: 1240, repos: ["frontend-web"] },
    ],
  },
  {
    developer_id: "dev_kiran_129",
    name: "Kiran R", email: "kiran@company.com",
    role: "developer", primary_tool: "None",
    avatar_initials: "KR", avatar_color: C.sub,
    sprint: {
      ai_spend_usd: 0, tickets_closed: 1,
      cost_per_ticket: 0, sessions: 0, ai_code_pct: 0,
      efficiency_score: 0, pr_size_avg: 280,
      commits_7d: [0, 0, 0, 0, 0, 0, 0],
      lines_added: 180, lines_deleted: 40, lines_accepted: 0,
      mode_breakdown: { agent: 0, chat: 0, edit: 0, plan: 0 },
      tokens_in: 0, tokens_out: 0,
    },
    agent_status: "never_installed", last_session_at: null,
    sessions: [],
    commit_breakdown: [],
  },
];

/* ─── Helpers ────────────────────────────────────────────── */
function Divider() {
  return <div style={{ height: 1, background: C.border }} />;
}

function Tag({ children, color, bg }: any) {
  return (
    <span style={{ padding: "2px 7px", borderRadius: 4, background: bg, color, fontFamily: F.mono, fontSize: 10, fontWeight: 600 }}>
      {children}
    </span>
  );
}

function AgentBadge({ status }: { status: string }) {
  const cfg = {
    active:          { label: "Agent active",    color: C.green, bg: C.greenBg },
    inactive:        { label: "Agent inactive",  color: C.amber, bg: C.amberBg },
    never_installed: { label: "Not installed",   color: C.red,   bg: C.redBg   },
  }[status] ?? { label: status, color: C.sub, bg: C.muted };
  return <Tag color={cfg.color} bg={cfg.bg}>{cfg.label}</Tag>;
}

function MiniBar({ values, color }: { values: number[]; color: string }) {
  const max = Math.max(...values, 1);
  return (
    <div style={{ display: "flex", gap: 2, alignItems: "flex-end", height: 20 }}>
      {values.map((v, i) => (
        <div key={i} style={{
          flex: 1, height: `${(v / max) * 18 + 2}px`,
          background: v === 0 ? C.muted : color,
          opacity: v === 0 ? 0.4 : 0.75, borderRadius: 2,
        }} />
      ))}
    </div>
  );
}

function EfficiencyRing({ score }: { score: number }) {
  const color = score >= 80 ? C.green : score >= 65 ? C.amber : score === 0 ? C.sub : C.red;
  const bg = score >= 80 ? C.greenBg : score >= 65 ? C.amberBg : score === 0 ? "rgba(90,90,90,0.1)" : C.redBg;
  return (
    <div style={{
      width: 38, height: 38, borderRadius: "50%",
      background: bg, display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: F.mono, fontSize: 12, fontWeight: 700, color,
    }}>
      {score > 0 ? score : "—"}
    </div>
  );
}

/* ─── Developer Detail Panel ─────────────────────────────── */
function DetailPanel({ dev, onClose }: { dev: typeof MOCK_PEOPLE[0]; onClose: () => void }) {
  const [tab, setTab] = useState<"profile" | "sessions">("profile");
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const s = dev.sprint;

  return (
    <div style={{
      position: "fixed", top: 0, right: 0, bottom: 0, width: 520,
      background: C.card, borderLeft: `1px solid ${C.borderHi}`,
      display: "flex", flexDirection: "column", zIndex: 100,
      boxShadow: "-24px 0 60px rgba(0,0,0,0.6)",
    }}>
      {/* Header */}
      <div style={{ padding: "20px 24px 16px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <div style={{
              width: 44, height: 44, borderRadius: "50%",
              background: `${dev.avatar_color}15`, border: `2px solid ${dev.avatar_color}40`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontFamily: F.mono, fontSize: 14, fontWeight: 700, color: dev.avatar_color,
            }}>
              {dev.avatar_initials}
            </div>
            <div>
              <div style={{ fontFamily: F.ui, fontSize: 16, fontWeight: 600, color: C.text }}>{dev.name}</div>
              <div style={{ fontFamily: F.body, fontSize: 12, color: C.sub, marginTop: 2 }}>
                {dev.role === "team_lead" ? "Team Lead" : "Developer"} · {dev.primary_tool}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", color: C.sub, padding: 4 }}
          >
            <X size={18} />
          </button>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <AgentBadge status={dev.agent_status} />
          {dev.last_session_at && (
            <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>
              Last session {new Date(dev.last_session_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: `1px solid ${C.border}` }}>
        {(["profile", "sessions"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            background: "none", border: "none", cursor: "pointer",
            fontFamily: F.body, fontSize: 13, fontWeight: tab === t ? 500 : 400,
            color: tab === t ? C.text : C.sub,
            padding: "10px 20px",
            borderBottom: tab === t ? `2px solid ${C.accent}` : "2px solid transparent",
          }}>
            {t === "profile" ? "Profile" : "Agent Sessions"}
          </button>
        ))}
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
        {tab === "profile" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* 7-day summary */}
            <div style={{ fontFamily: F.ui, fontSize: 12, fontWeight: 600, color: C.sub, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>
              Sprint 42 Summary
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              {[
                { label: "Sessions",         value: s.sessions.toString(),    color: C.accent },
                { label: "AI Spend",          value: `$${s.ai_spend_usd}`,     color: C.warm   },
                { label: "Tickets Closed",    value: s.tickets_closed.toString(), color: C.green },
                { label: "Cost / Ticket",     value: s.cost_per_ticket > 0 ? `$${s.cost_per_ticket.toFixed(2)}` : "—", color: C.text },
                { label: "Tokens In",         value: `${(s.tokens_in / 1000).toFixed(1)}k`, color: C.purple },
                { label: "Tokens Out",        value: `${(s.tokens_out / 1000).toFixed(1)}k`, color: C.purple },
              ].map((stat, i) => (
                <div key={i} style={{
                  background: C.surface, borderRadius: 8, padding: "10px 12px",
                  border: `1px solid ${C.border}`,
                }}>
                  <div style={{ fontFamily: F.body, fontSize: 10, color: C.sub, marginBottom: 4 }}>{stat.label}</div>
                  <div style={{ fontFamily: F.mono, fontSize: 16, fontWeight: 600, color: stat.color }}>{stat.value}</div>
                </div>
              ))}
            </div>

            {/* Mode breakdown */}
            <div style={{ background: C.surface, borderRadius: 8, padding: "12px 14px", border: `1px solid ${C.border}` }}>
              <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginBottom: 10 }}>Mode breakdown</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {Object.entries(s.mode_breakdown).map(([mode, pct]) => (
                  <div key={mode}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontFamily: F.body, fontSize: 11, color: C.text, textTransform: "capitalize" }}>{mode}</span>
                      <span style={{ fontFamily: F.mono, fontSize: 11, color: C.accent }}>{pct}%</span>
                    </div>
                    <div style={{ height: 3, background: C.muted, borderRadius: 2 }}>
                      <div style={{ height: "100%", width: `${pct}%`, background: C.accent, opacity: 0.6, borderRadius: 2 }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Commit cadence */}
            <div style={{ background: C.surface, borderRadius: 8, padding: "12px 14px", border: `1px solid ${C.border}` }}>
              <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginBottom: 8 }}>Commit cadence (last 7 days)</div>
              <div style={{ display: "flex", gap: 6, alignItems: "flex-end", height: 32, marginBottom: 4 }}>
                {s.commits_7d.map((c, i) => {
                  const max = Math.max(...s.commits_7d, 1);
                  return (
                    <div key={i} title={`${days[i]}: ${c}`} style={{
                      flex: 1, height: `${(c / max) * 28 + 2}px`,
                      background: c === 0 ? C.muted : C.accent,
                      opacity: c === 0 ? 0.3 : 0.75, borderRadius: 2,
                    }} />
                  );
                })}
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                {days.map(d => (
                  <div key={d} style={{ flex: 1, fontFamily: F.body, fontSize: 8, color: C.sub, textAlign: "center" }}>{d[0]}</div>
                ))}
              </div>
            </div>

            {/* Code output */}
            <div style={{ background: C.surface, borderRadius: 8, padding: "12px 14px", border: `1px solid ${C.border}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                <GitCommit size={13} color={C.sub} />
                <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>Commits this sprint</span>
                <span style={{ fontFamily: F.mono, fontSize: 11, color: C.sub, marginLeft: "auto" }}>Repositories</span>
              </div>
              {dev.commit_breakdown.map((cb, i) => (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                  background: C.card, borderRadius: 7, padding: "10px 12px",
                  border: `1px solid ${C.border}`, marginBottom: 6,
                }}>
                  <div>
                    <div style={{ fontFamily: F.mono, fontSize: 11, color: C.accent, marginBottom: 4 }}>{cb.tool.toUpperCase()}</div>
                    <div style={{ fontFamily: F.mono, fontSize: 13, fontWeight: 600, color: C.text }}>{cb.commits} commits</div>
                    <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>{cb.accepted_lines.toLocaleString()} accepted lines</div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 3, alignItems: "flex-end" }}>
                    {cb.repos.map(r => (
                      <span key={r} style={{
                        fontFamily: F.mono, fontSize: 9, color: C.sub,
                        background: C.muted, padding: "2px 6px", borderRadius: 4,
                      }}>
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Efficiency score */}
            <div style={{
              background: s.efficiency_score >= 80 ? C.greenBg : s.efficiency_score >= 65 ? C.amberBg : s.efficiency_score === 0 ? "rgba(90,90,90,0.05)" : C.redBg,
              border: `1px solid ${s.efficiency_score >= 80 ? "rgba(0,230,118,0.2)" : s.efficiency_score >= 65 ? "rgba(255,184,0,0.2)" : "rgba(90,90,90,0.15)"}`,
              borderRadius: 8, padding: "12px 14px",
              display: "flex", alignItems: "center", gap: 14,
            }}>
              <EfficiencyRing score={s.efficiency_score} />
              <div>
                <div style={{ fontFamily: F.body, fontSize: 12, color: C.text, fontWeight: 500 }}>
                  Efficiency Score: {s.efficiency_score > 0 ? `${s.efficiency_score}/100` : "No data yet"}
                </div>
                <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>
                  {s.efficiency_score >= 80 ? "Strong — high acceptance, consistent commits" :
                   s.efficiency_score >= 65 ? "Improving — some rework, watch PR size" :
                   s.efficiency_score === 0 ? "No AI sessions this sprint" :
                   "Needs attention — high rework rate"}
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === "sessions" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {dev.sessions.length === 0 ? (
              <div style={{ padding: "40px 0", textAlign: "center", fontFamily: F.body, fontSize: 13, color: C.sub }}>
                No sessions recorded this sprint
              </div>
            ) : dev.sessions.map((session, i) => {
              const riskColor = session.hallucination_risk === "alert" ? C.red : session.hallucination_risk === "watch" ? C.amber : C.green;
              const riskBg = session.hallucination_risk === "alert" ? C.redBg : session.hallucination_risk === "watch" ? C.amberBg : C.greenBg;
              return (
                <div key={i} style={{
                  background: C.surface, border: `1px solid ${session.hallucination_risk === "alert" ? "rgba(255,69,69,0.2)" : C.border}`,
                  borderRadius: 8, padding: "12px 14px",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                    <div>
                      <div style={{ fontFamily: F.mono, fontSize: 11, color: C.accent }}>{session.attribution?.ticket_id ?? "Unattributed"}</div>
                      <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>
                        {new Date(session.started_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })} · {session.active_duration_min}min · {session.tool}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 600, color: C.warm }}>${session.total_cost_usd.toFixed(2)}</span>
                      <Tag color={riskColor} bg={riskBg}>{session.hallucination_risk}</Tag>
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                    {[
                      { label: "Confidence", value: session.attribution ? `${Math.round(session.attribution.confidence * 100)}%` : "—" },
                      { label: "Lines added", value: session.lines_added.toString() },
                      { label: "Accepted",    value: session.lines_accepted.toString() },
                      { label: "Committed",   value: session.is_committed ? "Yes" : "No" },
                    ].map((stat, si) => (
                      <div key={si}>
                        <div style={{ fontFamily: F.body, fontSize: 9, color: C.sub, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>{stat.label}</div>
                        <div style={{ fontFamily: F.mono, fontSize: 12, color: C.text }}>{stat.value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── People List ────────────────────────────────────────── */
export default function PeoplePage() {
  const [selected, setSelected] = useState<typeof MOCK_PEOPLE[0] | null>(null);
  const [hov, setHov] = useState<string | null>(null);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
      `}</style>

      <div style={{ minHeight: "100vh", background: C.bg, fontFamily: F.body, color: C.text }}>
        {/* Page header */}
        <div style={{ borderBottom: `1px solid ${C.border}`, padding: "18px 28px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginBottom: 4 }}>Team · People</div>
            <h1 style={{ fontFamily: F.ui, fontSize: 22, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>People</h1>
            <div style={{ fontFamily: F.body, fontSize: 12, color: C.sub, marginTop: 4 }}>
              Per-developer AI usage and spend · Sprint 42
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={{ background: "none", border: `1px solid ${C.border}`, borderRadius: 7, padding: "7px 14px", cursor: "pointer", fontFamily: F.body, fontSize: 12, color: C.sub, display: "flex", alignItems: "center", gap: 6 }}>
              Sprint 42 <ChevronDown size={12} />
            </button>
            <button style={{ background: C.accentBg, border: `1px solid rgba(0,212,255,0.3)`, borderRadius: 7, padding: "7px 14px", cursor: "pointer", fontFamily: F.body, fontSize: 12, color: C.accent, display: "flex", alignItems: "center", gap: 6 }}>
              <Download size={12} /> Export
            </button>
          </div>
        </div>

        {/* Table */}
        <div style={{ padding: "22px 28px" }}>
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
            {/* Column headers */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 100px 70px 80px 80px 80px 100px 130px 70px", gap: 10, padding: "8px 20px" }}>
              {["Developer", "Primary Tool", "Sessions", "AI Spend", "Cost/Ticket", "AI Code %", "Efficiency", "Commits (7d)", "Status"].map(h => (
                <span key={h} style={{ fontFamily: F.body, fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>{h}</span>
              ))}
            </div>
            <Divider />

            {MOCK_PEOPLE.map((dev, i) => {
              const s = dev.sprint;
              const aiColor = s.ai_code_pct >= 80 ? C.green : s.ai_code_pct >= 60 ? C.amber : s.ai_code_pct === 0 ? C.sub : C.red;
              const isHov = hov === dev.developer_id;
              const isSel = selected?.developer_id === dev.developer_id;

              return (
                <div key={dev.developer_id}>
                  <div
                    onClick={() => setSelected(isSel ? null : dev)}
                    onMouseEnter={() => setHov(dev.developer_id)}
                    onMouseLeave={() => setHov(null)}
                    style={{
                      display: "grid", gridTemplateColumns: "1fr 100px 70px 80px 80px 80px 100px 130px 70px",
                      gap: 10, padding: "12px 20px", alignItems: "center",
                      background: isSel ? C.accentBg : isHov ? C.hover : "transparent",
                      cursor: "pointer", transition: "background .1s",
                      borderLeft: isSel ? `3px solid ${C.accent}` : "3px solid transparent",
                    }}
                  >
                    {/* Developer */}
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: "50%",
                        background: `${dev.avatar_color}15`, border: `1px solid ${dev.avatar_color}40`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontFamily: F.mono, fontSize: 10, fontWeight: 700, color: dev.avatar_color,
                        flexShrink: 0,
                      }}>
                        {dev.avatar_initials}
                      </div>
                      <div>
                        <div style={{ fontFamily: F.body, fontSize: 13, color: C.text, fontWeight: 500 }}>{dev.name}</div>
                        <div style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>
                          {dev.role === "team_lead" ? "Team Lead" : "Developer"}
                        </div>
                      </div>
                    </div>
                    {/* Primary tool */}
                    <span style={{ fontFamily: F.mono, fontSize: 11, color: C.sub }}>{dev.primary_tool}</span>
                    {/* Sessions */}
                    <span style={{ fontFamily: F.mono, fontSize: 12, color: s.sessions === 0 ? C.sub : C.text }}>{s.sessions}</span>
                    {/* AI Spend */}
                    <span style={{ fontFamily: F.mono, fontSize: 13, fontWeight: 600, color: s.ai_spend_usd > 0 ? C.warm : C.sub }}>
                      {s.ai_spend_usd > 0 ? `$${s.ai_spend_usd}` : "—"}
                    </span>
                    {/* Cost/ticket */}
                    <span style={{ fontFamily: F.mono, fontSize: 12, color: s.cost_per_ticket > 0 ? C.text : C.sub }}>
                      {s.cost_per_ticket > 0 ? `$${s.cost_per_ticket.toFixed(2)}` : "—"}
                    </span>
                    {/* AI code % */}
                    <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 600, color: aiColor }}>
                      {s.ai_code_pct > 0 ? `${s.ai_code_pct}%` : "—"}
                    </span>
                    {/* Efficiency */}
                    <div style={{ display: "flex", justifyContent: "flex-start" }}>
                      <EfficiencyRing score={s.efficiency_score} />
                    </div>
                    {/* Commit bars */}
                    <MiniBar values={s.commits_7d} color={C.accent} />
                    {/* Agent status */}
                    <AgentBadge status={dev.agent_status} />
                  </div>
                  {i < MOCK_PEOPLE.length - 1 && <Divider />}
                </div>
              );
            })}
          </div>
        </div>

        {/* Detail panel */}
        {selected && (
          <>
            <div
              onClick={() => setSelected(null)}
              style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 99 }}
            />
            <DetailPanel dev={selected} onClose={() => setSelected(null)} />
          </>
        )}
      </div>
    </>
  );
}

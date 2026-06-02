/**
 * S-01 Team Dashboard — v2
 * New Relic-inspired premium dark design.
 * Near-pure black, electric cyan accent, data-dense.
 * Layout is completely different from Exceeds.ai —
 * ticker strip + table hero + right panel + bottom grid.
 *
 * Dependencies: recharts, lucide-react
 * Fonts: Outfit (UI), JetBrains Mono (numbers), DM Sans (body)
 */

import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer,
  Tooltip, Cell, LineChart, Line,
} from "recharts";
import {
  LayoutDashboard, TrendingUp, DollarSign, Users,
  GitBranch, Bell, ChevronDown, AlertTriangle,
  Activity, GitPullRequest, Settings, Shield,
  Cpu, BarChart2, Eye, GitCommit, ChevronRight,
  ArrowUpRight, ArrowDownRight, Circle, Zap,
  MoreHorizontal, Clock, CheckCircle2, XCircle,
  AlertCircle, Search, Filter, Download,
} from "lucide-react";

/* ─── Tokens ────────────────────────────────────────────────── */
const C = {
  bg:       "#080808",
  card:     "#101010",
  surface:  "#181818",
  hover:    "#1E1E1E",
  accent:   "#00D4FF",
  accentBg: "rgba(0,212,255,0.08)",
  warm:     "#FFB547",
  warmBg:   "rgba(255,181,71,0.08)",
  green:    "#00E676",
  greenBg:  "rgba(0,230,118,0.08)",
  red:      "#FF4545",
  redBg:    "rgba(255,69,69,0.08)",
  amber:    "#FFB800",
  amberBg:  "rgba(255,184,0,0.08)",
  purple:   "#A78BFA",
  purpleBg: "rgba(167,139,250,0.08)",
  text:     "#F0F0F0",
  sub:      "#5A5A5A",
  muted:    "#2E2E2E",
  border:   "rgba(255,255,255,0.07)",
  borderHi: "rgba(255,255,255,0.14)",
} as const;

const F = {
  ui:   "'Outfit', sans-serif",
  body: "'DM Sans', sans-serif",
  mono: "'JetBrains Mono', monospace",
} as const;

/* ─── Data ──────────────────────────────────────────────────── */
const sprintData = [
  { sprint: "S37", cost: 218 }, { sprint: "S38", cost: 256 },
  { sprint: "S39", cost: 241 }, { sprint: "S40", cost: 289 },
  { sprint: "S41", cost: 280 }, { sprint: "S42", cost: 312 },
];

const tickets = [
  { id: "JIRA-142", title: "Stripe payment gateway",   dev: "Adnan K", tool: "Claude Code", cost: 4.20,  sessions: 3, conf: 87, status: "done",   risk: false },
  { id: "JIRA-151", title: "Data pipeline refactor",   dev: "Sara P",  tool: "Cursor",      cost: 8.40,  sessions: 7, conf: 71, status: "active",  risk: true  },
  { id: "JIRA-155", title: "Auth SSO integration",     dev: "Raj K",   tool: "Claude Code", cost: 3.10,  sessions: 2, conf: 92, status: "done",   risk: false },
  { id: "JIRA-159", title: "Search & filter API",      dev: "Priya M", tool: "Copilot",     cost: 6.80,  sessions: 5, conf: 68, status: "active",  risk: false },
  { id: "JIRA-163", title: "Mobile push notifications",dev: "Adnan K", tool: "Cursor",      cost: 2.90,  sessions: 2, conf: 55, status: "review",  risk: false },
  { id: "JIRA-167", title: "Analytics event tracking", dev: "Sara P",  tool: "Kiro",        cost: 11.20, sessions: 9, conf: 43, status: "active",  risk: true  },
];

const devData = [
  { name: "Adnan K",  spend: 142, sessions: 18, acceptance: 84, trend: +12, tool: "Claude Code" },
  { name: "Sara P",   spend: 98,  sessions: 14, acceptance: 71, trend: -4,  tool: "Cursor"      },
  { name: "Raj K",    spend: 67,  sessions: 9,  acceptance: 88, trend: +6,  tool: "Claude Code" },
  { name: "Priya M",  spend: 53,  sessions: 8,  acceptance: 76, trend: +2,  tool: "Copilot"     },
];

const tools = [
  { name: "Cursor",      pct: 52, cost: 648, color: C.accent  },
  { name: "Claude Code", pct: 22, cost: 274, color: C.purple  },
  { name: "Kiro",        pct: 14, cost: 175, color: C.warm    },
  { name: "Copilot",     pct: 12, cost: 150, color: C.green   },
];

const alerts = [
  { dev: "Sara P",  ticket: "JIRA-151", msg: "7 sessions, no commit in 3h", time: "42m ago", level: "high"   },
  { dev: "Adnan K", ticket: "JIRA-167", msg: "Token spike 4× avg at turn 9", time: "2h ago",  level: "medium" },
];

/* ─── Shared Components ─────────────────────────────────────── */
const Divider = () => (
  <div style={{ height: 1, background: C.border, margin: "0" }} />
);

function Tag({ children, color, bg }: { children: React.ReactNode; color: string; bg: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 7px", borderRadius: 4,
      background: bg, color, fontFamily: F.mono,
      fontSize: 10, fontWeight: 600, letterSpacing: "0.04em",
    }}>
      {children}
    </span>
  );
}

function ConfBadge({ conf }: { conf: number }) {
  const color = conf >= 80 ? C.green : conf >= 60 ? C.amber : C.red;
  const bg    = conf >= 80 ? C.greenBg : conf >= 60 ? C.amberBg : C.redBg;
  return <Tag color={color} bg={bg}>{conf}%</Tag>;
}

function StatusDot({ status }: { status: string }) {
  const cfg = {
    done:   { color: C.green,  label: "Done"    },
    active: { color: C.accent, label: "Active"  },
    review: { color: C.amber,  label: "Review"  },
  }[status] ?? { color: C.sub, label: status };
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: cfg.color, flexShrink: 0 }} />
      <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>{cfg.label}</span>
    </span>
  );
}

/* ─── Ticker Strip ──────────────────────────────────────────── */
function TickerStrip() {
  const items = [
    { label: "Sprint AI Spend",   value: "$312",  delta: "+$32",  up: true,  accent: C.accent },
    { label: "Cost per Ticket",   value: "$17.50",delta: "−$2.10",up: false, accent: C.warm   },
    { label: "Sessions Today",    value: "24",    delta: "+3",    up: true,  accent: C.text    },
    { label: "AI Adoption",       value: "71%",   delta: "+4%",   up: true,  accent: C.green   },
    { label: "Code Acceptance",   value: "76%",   delta: "−2%",   up: false, accent: C.text    },
    { label: "Unattributed",      value: "12",    delta: "needs review", up: null, accent: C.red },
  ];

  return (
    <div style={{
      display: "flex", alignItems: "stretch",
      borderBottom: `1px solid ${C.border}`,
      background: C.card,
    }}>
      {items.map((item, i) => (
        <div key={i} style={{
          flex: 1, padding: "12px 18px",
          borderRight: i < items.length - 1 ? `1px solid ${C.border}` : "none",
          display: "flex", flexDirection: "column", gap: 4,
        }}>
          <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            {item.label}
          </span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span style={{ fontFamily: F.mono, fontSize: 20, fontWeight: 600, color: item.accent, lineHeight: 1 }}>
              {item.value}
            </span>
            {item.up !== null ? (
              <span style={{
                fontFamily: F.mono, fontSize: 10,
                color: item.up ? C.green : C.red,
                display: "flex", alignItems: "center", gap: 2,
              }}>
                {item.up
                  ? <ArrowUpRight size={10} color={C.green} />
                  : <ArrowDownRight size={10} color={C.red} />}
                {item.delta}
              </span>
            ) : (
              <span style={{ fontFamily: F.mono, fontSize: 10, color: C.red }}>{item.delta}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─── Sprint Cost Table (hero) ──────────────────────────────── */
function SprintTable() {
  const [hovRow, setHovRow] = useState<number | null>(null);

  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
      {/* Table header */}
      <div style={{ padding: "14px 18px 10px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>
            Sprint Cost Intelligence
          </div>
          <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>
            Sprint 42 · Exact token cost per ticket · 15 tickets total
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button style={{
            display: "flex", alignItems: "center", gap: 5,
            background: "none", border: `1px solid ${C.border}`,
            borderRadius: 6, padding: "5px 10px", cursor: "pointer",
            fontFamily: F.body, fontSize: 11, color: C.sub,
          }}>
            <Filter size={11} /> Filter
          </button>
          <button style={{
            display: "flex", alignItems: "center", gap: 5,
            background: "none", border: `1px solid ${C.border}`,
            borderRadius: 6, padding: "5px 10px", cursor: "pointer",
            fontFamily: F.body, fontSize: 11, color: C.sub,
          }}>
            <Download size={11} /> Export
          </button>
        </div>
      </div>
      <Divider />

      {/* Column headers */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "140px 1fr 100px 80px 90px 80px 80px 80px",
        padding: "8px 18px",
        gap: 8,
      }}>
        {["Ticket", "Title", "Developer", "Tool", "AI Cost", "Sessions", "Confidence", "Status"].map((h, i) => (
          <span key={i} style={{
            fontFamily: F.body, fontSize: 10, color: C.sub,
            textTransform: "uppercase", letterSpacing: "0.08em",
            fontWeight: 600,
          }}>
            {h}
          </span>
        ))}
      </div>
      <Divider />

      {/* Rows */}
      {tickets.map((t, i) => (
        <div key={i}>
          <div
            onMouseEnter={() => setHovRow(i)}
            onMouseLeave={() => setHovRow(null)}
            style={{
              display: "grid",
              gridTemplateColumns: "140px 1fr 100px 80px 90px 80px 80px 80px",
              padding: "11px 18px", gap: 8, alignItems: "center",
              background: hovRow === i ? C.hover : "transparent",
              cursor: "pointer", transition: "background 0.1s",
            }}
          >
            {/* Ticket ID */}
            <span style={{ fontFamily: F.mono, fontSize: 12, color: C.accent }}>
              {t.risk && <AlertTriangle size={11} color={C.red} style={{ marginRight: 5, verticalAlign: "middle" }} />}
              {t.id}
            </span>
            {/* Title */}
            <span style={{ fontFamily: F.body, fontSize: 12, color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {t.title}
            </span>
            {/* Dev */}
            <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>{t.dev}</span>
            {/* Tool */}
            <span style={{ fontFamily: F.mono, fontSize: 10, color: C.sub }}>{t.tool.split(" ")[0]}</span>
            {/* Cost */}
            <span style={{ fontFamily: F.mono, fontSize: 13, fontWeight: 600, color: t.cost > 8 ? C.amber : C.text }}>
              ${t.cost.toFixed(2)}
            </span>
            {/* Sessions */}
            <span style={{ fontFamily: F.mono, fontSize: 12, color: C.sub }}>{t.sessions}</span>
            {/* Confidence */}
            <ConfBadge conf={t.conf} />
            {/* Status */}
            <StatusDot status={t.status} />
          </div>
          {i < tickets.length - 1 && <Divider />}
        </div>
      ))}

      {/* Footer */}
      <Divider />
      <div style={{
        padding: "10px 18px", display: "flex",
        alignItems: "center", justifyContent: "space-between",
      }}>
        <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>
          Showing 6 of 15 tickets · Sprint 42 total: <span style={{ color: C.accent, fontFamily: F.mono }}>$312.40</span>
        </span>
        <span style={{ fontFamily: F.body, fontSize: 11, color: C.accent, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
          View all tickets <ChevronRight size={12} />
        </span>
      </div>
    </div>
  );
}

/* ─── Right Panel ───────────────────────────────────────────── */
function RightPanel() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Tool breakdown */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 16px 10px" }}>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Tool Breakdown</div>
          <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>This sprint</div>
        </div>
        <Divider />
        <div style={{ padding: "10px 0" }}>
          {tools.map((t, i) => (
            <div key={i} style={{ padding: "8px 16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ width: 7, height: 7, borderRadius: 2, background: t.color, flexShrink: 0 }} />
                  <span style={{ fontFamily: F.body, fontSize: 12, color: C.text }}>{t.name}</span>
                </div>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <span style={{ fontFamily: F.mono, fontSize: 11, color: C.sub }}>${t.cost}</span>
                  <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 600, color: t.color }}>{t.pct}%</span>
                </div>
              </div>
              <div style={{ height: 3, background: C.muted, borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${t.pct}%`, background: t.color, borderRadius: 2, opacity: 0.7 }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Alerts */}
      <div style={{ background: C.card, border: `1px solid rgba(255,69,69,0.2)`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "12px 16px 10px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text, display: "flex", alignItems: "center", gap: 7 }}>
            <AlertTriangle size={13} color={C.red} /> Hallucination Alerts
          </div>
          <Tag color={C.red} bg={C.redBg}>{alerts.length} active</Tag>
        </div>
        <Divider />
        {alerts.map((a, i) => (
          <div key={i}>
            <div style={{ padding: "10px 16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontFamily: F.mono, fontSize: 11, color: a.level === "high" ? C.red : C.amber }}>
                  {a.dev} · {a.ticket}
                </span>
                <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>{a.time}</span>
              </div>
              <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>{a.msg}</div>
              <div style={{ marginTop: 8, display: "flex", gap: 6 }}>
                <button style={{
                  background: "none", border: `1px solid ${C.border}`,
                  borderRadius: 5, padding: "3px 9px", cursor: "pointer",
                  fontFamily: F.body, fontSize: 10, color: C.sub,
                }}>
                  View session
                </button>
                <button style={{
                  background: "none", border: `1px solid ${C.border}`,
                  borderRadius: 5, padding: "3px 9px", cursor: "pointer",
                  fontFamily: F.body, fontSize: 10, color: C.sub,
                }}>
                  DM developer
                </button>
              </div>
            </div>
            {i < alerts.length - 1 && <Divider />}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Bottom Section ────────────────────────────────────────── */
function BottomSection() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
      {/* Sprint trend */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px 10px" }}>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Sprint AI Spend Trend</div>
          <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>Last 6 sprints</div>
        </div>
        <Divider />
        <div style={{ padding: "12px 8px 8px" }}>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={sprintData} margin={{ top: 4, right: 8, bottom: 0, left: -12 }}>
              <XAxis
                dataKey="sprint"
                tick={{ fontSize: 10, fill: C.sub, fontFamily: F.body }}
                axisLine={false} tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: C.sub, fontFamily: F.body }}
                axisLine={false} tickLine={false}
                tickFormatter={v => `$${v}`}
              />
              <Tooltip
                contentStyle={{ background: C.surface, border: `1px solid ${C.borderHi}`, borderRadius: 6, fontFamily: F.mono, fontSize: 11 }}
                labelStyle={{ color: C.sub }}
                itemStyle={{ color: C.accent }}
                formatter={(v: number) => [`$${v}`, "AI Spend"]}
              />
              <Bar dataKey="cost" radius={[3, 3, 0, 0]}>
                {sprintData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={i === sprintData.length - 1 ? C.accent : "rgba(0,212,255,0.25)"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Developer table */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px 10px" }}>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Developer Efficiency</div>
          <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>This sprint · sorted by spend</div>
        </div>
        <Divider />
        <div style={{ padding: "6px 0" }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 60px 60px 70px 50px",
            padding: "4px 18px 8px", gap: 8,
          }}>
            {["Developer", "Spend", "Sessions", "Acceptance", "Trend"].map((h, i) => (
              <span key={i} style={{ fontFamily: F.body, fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>
                {h}
              </span>
            ))}
          </div>
          <Divider />
          {devData.map((d, i) => (
            <div key={i}>
              <div style={{
                display: "grid",
                gridTemplateColumns: "1fr 60px 60px 70px 50px",
                padding: "9px 18px", gap: 8, alignItems: "center",
              }}>
                <div>
                  <div style={{ fontFamily: F.body, fontSize: 12, color: C.text }}>{d.name}</div>
                  <div style={{ fontFamily: F.mono, fontSize: 10, color: C.sub }}>{d.tool}</div>
                </div>
                <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 600, color: C.warm }}>${d.spend}</span>
                <span style={{ fontFamily: F.mono, fontSize: 12, color: C.sub }}>{d.sessions}</span>
                <div style={{ height: 4, background: C.muted, borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${d.acceptance}%`, background: d.acceptance >= 80 ? C.green : d.acceptance >= 70 ? C.amber : C.red, borderRadius: 2 }} />
                </div>
                <span style={{
                  fontFamily: F.mono, fontSize: 11,
                  color: d.trend > 0 ? C.green : C.red,
                  display: "flex", alignItems: "center", gap: 2,
                }}>
                  {d.trend > 0
                    ? <ArrowUpRight size={10} color={C.green} />
                    : <ArrowDownRight size={10} color={C.red} />}
                  {Math.abs(d.trend)}%
                </span>
              </div>
              {i < devData.length - 1 && <Divider />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Sidebar ───────────────────────────────────────────────── */
function Sidebar() {
  const navItems = [
    { icon: LayoutDashboard, label: "Dashboard",   active: true  },
    { icon: TrendingUp,      label: "AI Insights"               },
    { icon: DollarSign,      label: "ROI"                        },
    { icon: Cpu,             label: "Agentic"                    },
    { icon: BarChart2,       label: "Metrics"                    },
    { icon: Activity,        label: "Capacity"                   },
    { icon: Eye,             label: "My Activity"                },
    { icon: Users,           label: "People"                     },
  ];

  return (
    <div style={{
      width: 48, minWidth: 48, height: "100vh",
      background: "#060606",
      borderRight: `1px solid ${C.border}`,
      display: "flex", flexDirection: "column",
      alignItems: "center", padding: "12px 0",
    }}>
      {/* Logo */}
      <div style={{
        width: 28, height: 28, borderRadius: 7,
        background: C.accentBg,
        border: `1px solid rgba(0,212,255,0.3)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        marginBottom: 20,
      }}>
        <Zap size={13} color={C.accent} />
      </div>

      {/* Nav */}
      <div style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {navItems.map((item, i) => (
          <div key={i} title={item.label} style={{
            width: 34, height: 34, borderRadius: 7,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer",
            background: item.active ? C.accentBg : "transparent",
            borderLeft: item.active ? `2px solid ${C.accent}` : "2px solid transparent",
            borderRadius: item.active ? "0 7px 7px 0" : 7,
            color: item.active ? C.accent : C.sub,
            transition: "all 0.12s",
          }}>
            <item.icon size={15} />
          </div>
        ))}
      </div>

      {/* Bottom */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "center" }}>
        <div style={{ position: "relative", cursor: "pointer" }}>
          <div style={{
            width: 34, height: 34, borderRadius: 7,
            display: "flex", alignItems: "center", justifyContent: "center",
            color: C.sub,
          }}>
            <GitBranch size={15} />
          </div>
          <span style={{
            position: "absolute", top: 4, right: 4,
            width: 14, height: 14, borderRadius: "50%",
            background: C.red,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: F.mono, fontSize: 8, fontWeight: 700, color: "#fff",
          }}>
            12
          </span>
        </div>
        <div style={{ width: 34, height: 34, borderRadius: 7, display: "flex", alignItems: "center", justifyContent: "center", color: C.sub, cursor: "pointer" }}>
          <Settings size={15} />
        </div>
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          background: C.accentBg,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: F.mono, fontSize: 9, fontWeight: 700, color: C.accent,
          cursor: "pointer",
        }}>
          AK
        </div>
      </div>
    </div>
  );
}

/* ─── Top Bar ───────────────────────────────────────────────── */
function TopBar() {
  return (
    <div style={{
      height: 48, display: "flex", alignItems: "center",
      justifyContent: "space-between",
      padding: "0 20px",
      borderBottom: `1px solid ${C.border}`,
      background: C.bg, flexShrink: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <h1 style={{ fontFamily: F.ui, fontSize: 15, fontWeight: 600, color: C.text, letterSpacing: "-0.02em" }}>
          Team Dashboard
        </h1>
        <div style={{
          display: "flex", alignItems: "center",
          background: C.card, border: `1px solid ${C.border}`,
          borderRadius: 6, padding: "4px 10px", gap: 6,
        }}>
          <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>Sprint 42</span>
          <span style={{ color: C.muted }}>·</span>
          <span style={{ fontFamily: F.mono, fontSize: 11, color: C.green }}>Active</span>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button style={{
          display: "flex", alignItems: "center", gap: 5,
          background: C.card, border: `1px solid ${C.border}`,
          borderRadius: 6, padding: "5px 10px", cursor: "pointer",
          fontFamily: F.body, fontSize: 11, color: C.text,
        }}>
          Last 30 days <ChevronDown size={11} color={C.sub} />
        </button>
        <button style={{
          display: "flex", alignItems: "center", gap: 5,
          background: C.card, border: `1px solid ${C.border}`,
          borderRadius: 6, padding: "5px 10px", cursor: "pointer",
          fontFamily: F.body, fontSize: 11, color: C.text,
        }}>
          All teams <ChevronDown size={11} color={C.sub} />
        </button>
        <div style={{ position: "relative", cursor: "pointer" }}>
          <div style={{
            width: 30, height: 30, borderRadius: 6,
            background: C.card, border: `1px solid ${C.border}`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Bell size={13} color={C.sub} />
          </div>
          <span style={{
            position: "absolute", top: 6, right: 6,
            width: 6, height: 6, borderRadius: "50%", background: C.red,
          }} />
        </div>
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          background: C.accentBg, border: `1px solid rgba(0,212,255,0.3)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: F.mono, fontSize: 9, fontWeight: 700, color: C.accent,
        }}>
          AK
        </div>
      </div>
    </div>
  );
}

/* ─── Root ──────────────────────────────────────────────────── */
export default function TeamDashboard() {
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
        button { outline: none; }
      `}</style>

      <div style={{
        display: "flex", height: "100vh", background: C.bg,
        fontFamily: F.body, color: C.text, overflow: "hidden",
      }}>
        <Sidebar />

        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <TopBar />
          <TickerStrip />

          {/* Main content */}
          <div style={{ flex: 1, overflowY: "auto", padding: "18px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Hero + Right panel */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 14 }}>
              <SprintTable />
              <RightPanel />
            </div>

            {/* Bottom */}
            <BottomSection />
          </div>
        </div>
      </div>
    </>
  );
}

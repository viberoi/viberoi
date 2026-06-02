/**
 * S-02 AI Insights
 * Deep AI adoption and quality metrics for Engineering Managers.
 * Shows KPI 1-7: contribution, productivity, quality, adoption,
 * tools breakdown, PR size, commits per dev.
 *
 * Same design system as TeamDashboard + ROIView.
 * Shared mock data: Sprint 42, 8 developers, Acme Engineering.
 */

import { useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  ResponsiveContainer, Tooltip, Cell, LineChart, Line,
} from "recharts";
import {
  TrendingUp, Shield, Users, GitCommit, GitPullRequest,
  ChevronDown, ArrowUpRight, ArrowDownRight, Download,
  Info, AlertTriangle, ChevronRight, Zap,
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

/* ─── Shared Data ────────────────────────────────────────── */
const weeks = ["W1","W2","W3","W4","W5","W6","W7","W8"];

const adoptionData = weeks.map((w, i) => ({
  w, v: [62, 71, 58, 83, 76, 89, 74, 91][i],
}));

const qualityData = weeks.map((w, i) => ({
  w,
  accepted: [78, 80, 76, 82, 79, 81, 74, 76][i],
  reverted: [22, 20, 24, 18, 21, 19, 26, 24][i],
}));

const prSizeData = [
  { w: "W1", ai: 820,  human: 420  },
  { w: "W2", ai: 1240, human: 380  },
  { w: "W3", ai: 960,  human: 450  },
  { w: "W4", ai: 1580, human: 390  },
  { w: "W5", ai: 1320, human: 420  },
  { w: "W6", ai: 1890, human: 400  },
  { w: "W7", ai: 1640, human: 410  },
  { w: "W8", ai: 2100, human: 430  },
];

const developers = [
  { name: "Adnan K",  tool: "Claude Code", contribution: 84, adoption: true,  commits: [3,5,4,6,5,1,0], sessions: 18, prSize: 980  },
  { name: "Sara P",   tool: "Cursor",      contribution: 71, adoption: true,  commits: [2,4,3,5,4,0,0], sessions: 14, prSize: 2100 },
  { name: "Raj K",    tool: "Claude Code", contribution: 88, adoption: true,  commits: [4,6,5,7,5,2,1], sessions: 9,  prSize: 720  },
  { name: "Priya M",  tool: "Copilot",     contribution: 76, adoption: true,  commits: [2,3,4,4,3,0,0], sessions: 8,  prSize: 850  },
  { name: "Vikram S", tool: "Cursor",      contribution: 69, adoption: true,  commits: [1,2,2,3,2,0,0], sessions: 6,  prSize: 1100 },
  { name: "Meera T",  tool: "Cursor",      contribution: 45, adoption: false, commits: [0,1,1,2,1,0,0], sessions: 3,  prSize: 430  },
  { name: "Dev A",    tool: "Copilot",     contribution: 55, adoption: true,  commits: [1,2,1,2,2,0,0], sessions: 4,  prSize: 620  },
  { name: "Kiran R",  tool: "None",        contribution: 0,  adoption: false, commits: [0,0,0,0,0,0,0], sessions: 0,  prSize: 280  },
];

const toolsBreakdown = [
  { name: "Cursor",      pct: 52, sessions: 312, cost: 648, color: C.accent  },
  { name: "Claude Code", pct: 22, sessions: 132, cost: 274, color: C.purple  },
  { name: "Kiro",        pct: 14, sessions: 84,  cost: 175, color: C.warm    },
  { name: "Copilot",     pct: 12, sessions: 72,  cost: 150, color: C.green   },
];

/* ─── Shared Components ──────────────────────────────────── */
function Divider() {
  return <div style={{ height: 1, background: C.border }} />;
}

function Tag({ children, color, bg }: any) {
  return (
    <span style={{
      padding: "2px 7px", borderRadius: 4,
      background: bg, color,
      fontFamily: F.mono, fontSize: 10, fontWeight: 600,
    }}>
      {children}
    </span>
  );
}

function CardHeader({ title, sub, action }: { title: string; sub?: string; action?: React.ReactNode }) {
  return (
    <>
      <div style={{ padding: "14px 18px 10px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>{title}</div>
          {sub && <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>{sub}</div>}
        </div>
        {action}
      </div>
      <Divider />
    </>
  );
}

const ChartTooltip = ({ active, payload, label, unit = "" }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: C.surface, border: `1px solid ${C.borderHi}`,
      borderRadius: 7, padding: "8px 12px",
    }}>
      <div style={{ fontFamily: F.body, fontSize: 10, color: C.sub, marginBottom: 4 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ fontFamily: F.mono, fontSize: 12, color: p.color || C.accent, fontWeight: 600 }}>
          {p.value}{unit}
        </div>
      ))}
    </div>
  );
};

/* ─── KPI Header Cards ───────────────────────────────────── */
function KPIStrip() {
  const kpis = [
    { label: "AI-Authored Code %",    value: "82%",   delta: "+12%",  up: true,  color: C.accent, status: "HEALTHY" },
    { label: "Productivity Lift",      value: "1.44x", delta: "+0.2x", up: true,  color: C.purple, status: "WATCH"   },
    { label: "Code Acceptance Rate",   value: "76%",   delta: "−2%",   up: false, color: C.warm,   status: "HEALTHY" },
    { label: "Team AI Adoption",       value: "71%",   delta: "+4%",   up: true,  color: C.green,  status: "GOOD"    },
  ];

  const statusColor: Record<string, string> = {
    HEALTHY: C.green, WATCH: C.amber, GOOD: C.green, "AT RISK": C.red,
  };
  const statusBg: Record<string, string> = {
    HEALTHY: C.greenBg, WATCH: C.amberBg, GOOD: C.greenBg, "AT RISK": C.redBg,
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
      {kpis.map((k, i) => (
        <div key={i} style={{
          background: C.card, border: `1px solid ${C.border}`,
          borderRadius: 10, padding: "14px 16px",
          display: "flex", flexDirection: "column", gap: 10,
          transition: "border-color .15s",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>{k.label}</span>
            <Tag color={statusColor[k.status]} bg={statusBg[k.status]}>{k.status}</Tag>
          </div>
          <div>
            <div style={{ fontFamily: F.mono, fontSize: 28, fontWeight: 600, color: k.color, lineHeight: 1 }}>{k.value}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 5 }}>
              {k.up ? <ArrowUpRight size={10} color={C.green} /> : <ArrowDownRight size={10} color={C.red} />}
              <span style={{ fontFamily: F.mono, fontSize: 10, color: k.up ? C.green : C.red }}>{k.delta} vs last period</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─── AI Adoption Chart ──────────────────────────────────── */
function AdoptionChart() {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
      <CardHeader title="Team AI Adoption" sub="% of active developers using AI tools per week · last 8 weeks" />
      <div style={{ padding: "12px 8px 8px" }}>
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={adoptionData} margin={{ top: 4, right: 12, bottom: 0, left: -12 }}>
            <defs>
              <linearGradient id="adoptGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={C.accent} stopOpacity={0.2} />
                <stop offset="95%" stopColor={C.accent} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="w" tick={{ fontSize: 10, fill: C.sub, fontFamily: F.body }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: C.sub, fontFamily: F.body }} axisLine={false} tickLine={false} domain={[0, 100]} tickFormatter={v => `${v}%`} />
            <Tooltip content={<ChartTooltip unit="%" />} />
            <Area type="monotone" dataKey="v" name="Adoption" stroke={C.accent} strokeWidth={2} fill="url(#adoptGrad)" dot={false} activeDot={{ r: 4, fill: C.accent }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <Divider />
      <div style={{ padding: "10px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>
          2 developers not yet using AI tools. <span style={{ color: C.amber }}>Meera T, Kiran R</span> — send nudge?
        </span>
        <span style={{ fontFamily: F.body, fontSize: 11, color: C.accent, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
          View by developer <ChevronRight size={12} />
        </span>
      </div>
    </div>
  );
}

/* ─── Code Quality Chart ─────────────────────────────────── */
function QualityChart() {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
      <CardHeader title="Code Acceptance Rate" sub="AI-generated lines accepted vs reverted · weekly trend" />
      <div style={{ padding: "12px 8px 8px" }}>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={qualityData} margin={{ top: 4, right: 12, bottom: 0, left: -12 }}>
            <XAxis dataKey="w" tick={{ fontSize: 10, fill: C.sub, fontFamily: F.body }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: C.sub, fontFamily: F.body }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
            <Tooltip content={<ChartTooltip unit="%" />} />
            <Bar dataKey="accepted" name="Accepted" fill={C.accent} fillOpacity={0.7} radius={[3, 3, 0, 0]} stackId="a" />
            <Bar dataKey="reverted" name="Reverted" fill={C.red} fillOpacity={0.5} radius={[3, 3, 0, 0]} stackId="a" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Divider />
      <div style={{ padding: "10px 18px", display: "flex", gap: 16 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: F.body, fontSize: 11, color: C.sub }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: C.accent, opacity: 0.7 }} />
          Accepted
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: F.body, fontSize: 11, color: C.sub }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: C.red, opacity: 0.5 }} />
          Reverted
        </span>
      </div>
    </div>
  );
}

/* ─── Tools Breakdown ────────────────────────────────────── */
function ToolsBreakdown() {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
      <CardHeader title="AI Tools Breakdown" sub="Session distribution by tool · Sprint 42" />
      <div style={{ padding: "10px 0" }}>
        {toolsBreakdown.map((t, i) => (
          <div key={i}>
            <div style={{ padding: "10px 18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: t.color, flexShrink: 0 }} />
                  <span style={{ fontFamily: F.body, fontSize: 12, color: C.text }}>{t.name}</span>
                </div>
                <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
                  <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub }}>{t.sessions} sessions</span>
                  <span style={{ fontFamily: F.mono, fontSize: 11, color: C.warm }}>${t.cost}</span>
                  <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 700, color: t.color, width: 36, textAlign: "right" }}>{t.pct}%</span>
                </div>
              </div>
              <div style={{ height: 4, background: C.muted, borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${t.pct}%`, background: t.color, borderRadius: 2, opacity: 0.75 }} />
              </div>
            </div>
            {i < toolsBreakdown.length - 1 && <Divider />}
          </div>
        ))}
      </div>
      <Divider />
      <div style={{ padding: "10px 18px" }}>
        <div style={{
          background: C.accentBg, border: `1px solid rgba(0,212,255,0.15)`,
          borderRadius: 8, padding: "10px 14px",
          fontFamily: F.body, fontSize: 11, color: C.sub,
        }}>
          💡 Cursor accounts for 52% of sessions but only 2 developers primarily use Claude Code.
          Claude Code sessions show 12% higher acceptance rates on average.
        </div>
      </div>
    </div>
  );
}

/* ─── PR Size Chart ──────────────────────────────────────── */
function PRSizeChart() {
  return (
    <div style={{ background: C.card, border: `1px solid rgba(255,69,69,0.2)`, borderRadius: 10, overflow: "hidden" }}>
      <CardHeader
        title="AI PR Size vs Human PR Size"
        sub="Average lines of code per PR · AI-assisted vs human-only"
        action={<Tag color={C.red} bg={C.redBg}>AT RISK</Tag>}
      />
      <div style={{ padding: "12px 8px 8px" }}>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={prSizeData} margin={{ top: 4, right: 12, bottom: 0, left: -12 }}>
            <XAxis dataKey="w" tick={{ fontSize: 10, fill: C.sub, fontFamily: F.body }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: C.sub, fontFamily: F.body }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip unit=" LOC" />} />
            <Bar dataKey="ai" name="AI-assisted" radius={[3, 3, 0, 0]}>
              {prSizeData.map((_, i) => (
                <Cell key={i} fill={C.red} fillOpacity={_ .ai > 1500 ? 0.8 : 0.35} />
              ))}
            </Bar>
            <Bar dataKey="human" name="Human-only" fill={C.accent} fillOpacity={0.3} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Divider />
      <div style={{ padding: "10px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 16 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: F.body, fontSize: 11, color: C.sub }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: C.red, opacity: 0.8 }} /> AI-assisted
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: F.body, fontSize: 11, color: C.sub }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: C.accent, opacity: 0.3 }} /> Human-only
          </span>
        </div>
        <span style={{ fontFamily: F.mono, fontSize: 11, color: C.red }}>⚠ AI PRs 4.9× larger than human PRs</span>
      </div>
    </div>
  );
}

/* ─── Developer Adoption Table ───────────────────────────── */
function DeveloperTable() {
  const [hov, setHov] = useState<number | null>(null);
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
      <CardHeader
        title="Developer AI Breakdown"
        sub="Individual contribution rates and session patterns · Sprint 42"
        action={
          <button style={{
            background: "none", border: `1px solid ${C.border}`,
            borderRadius: 6, padding: "4px 10px", cursor: "pointer",
            fontFamily: F.body, fontSize: 11, color: C.sub,
            display: "flex", alignItems: "center", gap: 5,
          }}>
            <Filter size={11} /> Filter
          </button>
        }
      />
      {/* Column headers */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 60px 80px 70px 140px 60px", gap: 10, padding: "6px 18px" }}>
        {["Developer", "Tool", "Sessions", "AI Code %", "PR Size", "Commit cadence (7d)", "Status"].map(h => (
          <span key={h} style={{ fontFamily: F.body, fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>{h}</span>
        ))}
      </div>
      <Divider />
      {developers.map((d, i) => {
        const codeColor = d.contribution >= 80 ? C.green : d.contribution >= 60 ? C.amber : d.contribution === 0 ? C.sub : C.red;
        const prColor = d.prSize > 1500 ? C.red : d.prSize > 1000 ? C.amber : C.text;
        const maxCommit = Math.max(...d.commits, 1);

        return (
          <div key={i}>
            <div
              onMouseEnter={() => setHov(i)}
              onMouseLeave={() => setHov(null)}
              style={{
                display: "grid", gridTemplateColumns: "1fr 80px 60px 80px 70px 140px 60px",
                gap: 10, padding: "10px 18px", alignItems: "center",
                background: hov === i ? C.hover : "transparent",
                cursor: "pointer", transition: "background .1s",
              }}
            >
              {/* Name */}
              <div>
                <div style={{ fontFamily: F.body, fontSize: 12, color: C.text }}>{d.name}</div>
              </div>
              {/* Tool */}
              <span style={{ fontFamily: F.mono, fontSize: 10, color: C.sub }}>{d.tool}</span>
              {/* Sessions */}
              <span style={{ fontFamily: F.mono, fontSize: 12, color: d.sessions === 0 ? C.sub : C.text }}>{d.sessions}</span>
              {/* AI Code % */}
              <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 600, color: codeColor }}>{d.contribution > 0 ? `${d.contribution}%` : "—"}</span>
              </div>
              {/* PR Size */}
              <span style={{ fontFamily: F.mono, fontSize: 12, color: prColor }}>{d.prSize > 0 ? `${d.prSize}` : "—"}</span>
              {/* Commit sparkline */}
              <div style={{ display: "flex", gap: 3, alignItems: "flex-end", height: 24 }}>
                {d.commits.map((c, ci) => (
                  <div key={ci} title={`${days[ci]}: ${c} commits`} style={{
                    flex: 1, height: `${(c / maxCommit) * 22 + 2}px`,
                    background: c === 0 ? C.muted : C.accent,
                    opacity: c === 0 ? 0.4 : 0.7,
                    borderRadius: 2, transition: "opacity .1s",
                  }} />
                ))}
              </div>
              {/* Status */}
              {d.adoption
                ? <Tag color={C.green} bg={C.greenBg}>Active</Tag>
                : <Tag color={C.red} bg={C.redBg}>No AI</Tag>}
            </div>
            {i < developers.length - 1 && <Divider />}
          </div>
        );
      })}
    </div>
  );
}

/* ─── Root ───────────────────────────────────────────────── */
// Needed for filter button
function Filter({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  );
}

export default function AIInsights() {
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
        <div style={{ borderBottom: `1px solid ${C.border}`, padding: "18px 28px 16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginBottom: 4 }}>Insights · AI Insights</div>
              <h1 style={{ fontFamily: F.ui, fontSize: 22, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>AI Insights</h1>
              <div style={{ fontFamily: F.body, fontSize: 12, color: C.sub, marginTop: 4 }}>
                Adoption, code quality, and tool breakdown across your engineering team
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button style={{
                background: "none", border: `1px solid ${C.border}`,
                borderRadius: 7, padding: "7px 14px", cursor: "pointer",
                fontFamily: F.body, fontSize: 12, color: C.sub,
                display: "flex", alignItems: "center", gap: 6,
              }}>
                All teams <ChevronDown size={12} />
              </button>
              <button style={{
                background: "none", border: `1px solid ${C.border}`,
                borderRadius: 7, padding: "7px 14px", cursor: "pointer",
                fontFamily: F.body, fontSize: 12, color: C.sub,
                display: "flex", alignItems: "center", gap: 6,
              }}>
                Last 30 days <ChevronDown size={12} />
              </button>
              <button style={{
                background: C.accentBg, border: `1px solid rgba(0,212,255,0.3)`,
                borderRadius: 7, padding: "7px 14px", cursor: "pointer",
                fontFamily: F.body, fontSize: 12, color: C.accent,
                display: "flex", alignItems: "center", gap: 6,
              }}>
                <Download size={12} /> Export
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: "22px 28px", display: "flex", flexDirection: "column", gap: 14 }}>
          <KPIStrip />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <AdoptionChart />
            <QualityChart />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <ToolsBreakdown />
            <PRSizeChart />
          </div>

          <DeveloperTable />
        </div>
      </div>
    </>
  );
}

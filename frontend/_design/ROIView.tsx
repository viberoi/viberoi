/**
 * S-03 ROI View
 * The CFO screen. 5 tabs: Summary, Developer Impact,
 * How AI Is Used, Features, Activity.
 * Near-black + electric cyan design system.
 */

import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip,
  Cell, AreaChart, Area, LineChart, Line, PieChart, Pie,
} from "recharts";
import {
  DollarSign, TrendingUp, Users, Clock, ArrowUpRight,
  ArrowDownRight, ChevronRight, BarChart2, Activity,
  GitCommit, Zap, AlertTriangle, Filter, Download,
  ChevronDown,
} from "lucide-react";

/* ─── Tokens ─────────────────────────────────────────────── */
const C = {
  bg:      "#080808", card:    "#101010", surface: "#181818",
  hover:   "#1E1E1E", accent:  "#00D4FF", accentBg:"rgba(0,212,255,0.08)",
  warm:    "#FFB547", warmBg:  "rgba(255,181,71,0.08)",
  green:   "#00E676", greenBg: "rgba(0,230,118,0.08)",
  red:     "#FF4545", redBg:   "rgba(255,69,69,0.08)",
  amber:   "#FFB800", amberBg: "rgba(255,184,0,0.08)",
  purple:  "#A78BFA", purpleBg:"rgba(167,139,250,0.08)",
  text:    "#F0F0F0", sub:     "#5A5A5A", muted: "#2E2E2E",
  border:  "rgba(255,255,255,0.07)",
  borderHi:"rgba(255,255,255,0.14)",
} as const;

const F = {
  ui:   "'Outfit', sans-serif",
  body: "'DM Sans', sans-serif",
  mono: "'JetBrains Mono', monospace",
};

/* ─── Data ───────────────────────────────────────────────── */
const dailyROI = Array.from({ length: 90 }, (_, i) => {
  const val = (Math.random() - 0.35) * 3;
  return { day: i, val: +val.toFixed(2) };
});

const spendByFeature = [
  { feature: "Auth & Onboarding",    epic: "Login, signup, SSO, MFA",        cost: 6000, loc: "14.2k", roi: 3.8,  trend: "up"   },
  { feature: "Checkout & Payments",  epic: "Cart, billing, refunds",          cost: 5400, loc: "9.8k",  roi: 4.6,  trend: "up"   },
  { feature: "Internal Tools",       epic: "Admin, ops, support consoles",     cost: 4800, loc: "22.4k", roi: 5.1,  trend: "up"   },
  { feature: "Search & Discovery",   epic: "Search, recs, filters",            cost: 4200, loc: "7.6k",  roi: 2.4,  trend: "up"   },
  { feature: "Data Pipelines",       epic: "ETL, batch jobs, transforms",      cost: 3600, loc: "6.4k",  roi: -0.8, trend: "down" },
  { feature: "Notifications",        epic: "Email, push, webhooks",            cost: 2100, loc: "4.1k",  roi: 1.9,  trend: "up"   },
];

const devImpact = [
  { name: "Adnan K",  cost: 142, tickets: 8,  costPerTicket: 17.75, aiCode: 84, score: 78, tool: "Claude Code" },
  { name: "Sara P",   cost: 98,  tickets: 6,  costPerTicket: 16.33, aiCode: 71, score: 82, tool: "Cursor"      },
  { name: "Raj K",    cost: 67,  tickets: 7,  costPerTicket: 9.57,  aiCode: 88, score: 91, tool: "Claude Code" },
  { name: "Priya M",  cost: 53,  tickets: 5,  costPerTicket: 10.60, aiCode: 76, score: 74, tool: "Copilot"     },
  { name: "Vikram S", cost: 38,  tickets: 4,  costPerTicket: 9.50,  aiCode: 69, score: 68, tool: "Cursor"      },
];

const modeData = [
  { mode: "Agent",  pct: 62, color: C.accent  },
  { mode: "Chat",   pct: 18, color: C.purple  },
  { mode: "Edit",   pct: 12, color: C.warm    },
  { mode: "Plan",   pct: 8,  color: C.green   },
];

const modelUsage = [
  { model: "claude-sonnet-4",  sessions: 412 },
  { model: "claude-haiku-4",   sessions: 189 },
  { model: "gpt-4o",           sessions: 98  },
  { model: "cursor-small",     sessions: 74  },
  { model: "claude-opus-4",    sessions: 41  },
];

const sessionLen = [
  { range: "0–15m",  count: 124 },
  { range: "15–30m", count: 198 },
  { range: "30–60m", count: 241 },
  { range: "60–90m", count: 87  },
  { range: "90m+",   count: 34  },
];

const activityHeatmap = Array.from({ length: 7 }, (_, d) =>
  Array.from({ length: 12 }, (_, h) => ({
    day: ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d],
    hour: `${8 + h}:00`,
    val: Math.floor(Math.random() * 12),
  }))
).flat();

/* ─── Shared ─────────────────────────────────────────────── */
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

function SummaryCard({
  label, value, sub, color, icon: Icon, delta, deltaUp,
}: any) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: C.card,
        border: `1px solid ${hov ? C.borderHi : C.border}`,
        borderRadius: 10, padding: "16px 18px",
        transition: "border-color .15s, transform .15s",
        transform: hov ? "translateY(-1px)" : "none",
        display: "flex", flexDirection: "column", gap: 10,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: F.body, fontSize: 11, color: C.sub, textTransform: "uppercase", letterSpacing: "0.07em" }}>
          {label}
        </span>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Icon size={13} color={color} />
        </div>
      </div>
      <div>
        <div style={{ fontFamily: F.mono, fontSize: 32, fontWeight: 600, color, lineHeight: 1, letterSpacing: "-0.02em" }}>
          {value}
        </div>
        <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 4 }}>{sub}</div>
      </div>
      {delta && (
        <div style={{ display: "flex", alignItems: "center", gap: 4, fontFamily: F.mono, fontSize: 10, color: deltaUp ? C.green : C.red }}>
          {deltaUp ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
          {delta} vs last 90 days
        </div>
      )}
    </div>
  );
}

/* ─── Tab: Summary ───────────────────────────────────────── */
function TabSummary() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <SummaryCard label="Blended AI ROI" value="3.8x" sub="Across all models and tools" color={C.accent} icon={TrendingUp} delta="+0.6x" deltaUp />
        <SummaryCard label="Total AI Spend" value="$26.1k" sub="Last 90 days, all tools" color={C.warm} icon={DollarSign} delta="+$4.2k" deltaUp />
        <SummaryCard label="Avg Engineer Spend" value="$182" sub="Per developer per month" color={C.purple} icon={Users} delta="+$22" deltaUp />
        <SummaryCard label="Tickets Shipped" value="148" sub="AI-attributed, last 90 days" color={C.green} icon={GitCommit} delta="+31" deltaUp />
      </div>

      {/* Daily ROI heatmap */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px 10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Daily AI ROI</div>
            <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>Last 90 days · value shipped per $ spent</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16, fontFamily: F.mono, fontSize: 10 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span style={{ width: 24, height: 6, borderRadius: 2, background: C.red, display: "inline-block" }} />
              <span style={{ color: C.sub }}>Loss</span>
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span style={{ width: 24, height: 6, borderRadius: 2, background: C.muted, display: "inline-block" }} />
              <span style={{ color: C.sub }}>Break-even</span>
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span style={{ width: 24, height: 6, borderRadius: 2, background: C.accent, display: "inline-block" }} />
              <span style={{ color: C.sub }}>Gain</span>
            </span>
          </div>
        </div>
        <Divider />
        <div style={{ padding: "14px 18px 10px", display: "flex", gap: 3, alignItems: "flex-end" }}>
          {dailyROI.map((d, i) => {
            const h = Math.abs(d.val) * 18 + 4;
            const color = d.val > 0.5 ? C.accent : d.val < -0.2 ? C.red : C.muted;
            return (
              <div key={i} title={`Day ${i + 1}: ${d.val > 0 ? "+" : ""}${d.val}x ROI`} style={{
                flex: 1, height: h, borderRadius: 2,
                background: color, opacity: Math.abs(d.val) * 0.4 + 0.3,
                minWidth: 2, cursor: "pointer",
                transition: "opacity .1s",
              }} />
            );
          })}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", padding: "0 18px 10px" }}>
          <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>90 days ago</span>
          <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>60d</span>
          <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>30d</span>
          <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>Today</span>
        </div>
      </div>

      {/* Spend by feature table */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px 10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Spend by Feature</div>
            <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>Where AI dollars went · last 90 days</div>
          </div>
          <button style={{
            background: "none", border: `1px solid ${C.border}`,
            borderRadius: 6, padding: "4px 10px", cursor: "pointer",
            fontFamily: F.body, fontSize: 11, color: C.sub,
            display: "flex", alignItems: "center", gap: 5,
          }}>
            <Download size={11} /> Export
          </button>
        </div>
        <Divider />
        {/* Column headers */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 60px 200px 80px", gap: 12, padding: "7px 18px" }}>
          {["Feature Category", "Cost", "LOC", "ROI (bar)", "ROI"].map((h, i) => (
            <span key={i} style={{ fontFamily: F.body, fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>
              {h}
            </span>
          ))}
        </div>
        <Divider />
        {spendByFeature.map((f, i) => {
          const isNeg = f.roi < 0;
          const barWidth = Math.min(Math.abs(f.roi) / 5.5 * 100, 100);
          return (
            <div key={i}>
              <div style={{
                display: "grid", gridTemplateColumns: "1fr 80px 60px 200px 80px",
                gap: 12, padding: "12px 18px", alignItems: "center",
                background: isNeg ? "rgba(255,69,69,0.03)" : "transparent",
                cursor: "pointer",
              }}>
                {/* Feature */}
                <div>
                  <div style={{ fontFamily: F.body, fontSize: 12, color: C.text, fontWeight: 500 }}>{f.feature}</div>
                  <div style={{ fontFamily: F.body, fontSize: 10, color: C.sub, marginTop: 2 }}>{f.epic}</div>
                </div>
                {/* Cost */}
                <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 600, color: C.warm }}>
                  ${(f.cost / 1000).toFixed(1)}k
                </span>
                {/* LOC */}
                <span style={{ fontFamily: F.mono, fontSize: 11, color: C.sub }}>{f.loc}</span>
                {/* Bar */}
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{ flex: 1, height: 6, background: C.muted, borderRadius: 3, overflow: "hidden" }}>
                    <div style={{
                      height: "100%", width: `${barWidth}%`,
                      background: isNeg ? C.red : C.accent,
                      borderRadius: 3, opacity: 0.8,
                    }} />
                  </div>
                </div>
                {/* ROI */}
                <Tag
                  color={isNeg ? C.red : C.green}
                  bg={isNeg ? C.redBg : C.greenBg}
                >
                  {isNeg ? "" : "+"}{f.roi}x
                </Tag>
              </div>
              {i < spendByFeature.length - 1 && <Divider />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Tab: Developer Impact ──────────────────────────────── */
function TabDevImpact() {
  const [hov, setHov] = useState<number | null>(null);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px 10px" }}>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Developer ROI Breakdown</div>
          <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>AI cost and output per developer · last 30 days</div>
        </div>
        <Divider />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 70px 70px 90px 80px 90px", gap: 10, padding: "7px 18px" }}>
          {["Developer", "AI Cost", "Tickets", "Cost/Ticket", "AI Code %", "Efficiency"].map(h => (
            <span key={h} style={{ fontFamily: F.body, fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>{h}</span>
          ))}
        </div>
        <Divider />
        {devImpact.map((d, i) => (
          <div key={i}>
            <div
              onMouseEnter={() => setHov(i)}
              onMouseLeave={() => setHov(null)}
              style={{
                display: "grid", gridTemplateColumns: "1fr 70px 70px 90px 80px 90px",
                gap: 10, padding: "11px 18px", alignItems: "center",
                background: hov === i ? C.hover : "transparent",
                cursor: "pointer", transition: "background .1s",
              }}
            >
              <div>
                <div style={{ fontFamily: F.body, fontSize: 12, color: C.text }}>{d.name}</div>
                <div style={{ fontFamily: F.mono, fontSize: 10, color: C.sub }}>{d.tool}</div>
              </div>
              <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 600, color: C.warm }}>${d.cost}</span>
              <span style={{ fontFamily: F.mono, fontSize: 12, color: C.sub }}>{d.tickets}</span>
              <span style={{ fontFamily: F.mono, fontSize: 12, color: C.text }}>${d.costPerTicket.toFixed(2)}</span>
              <div style={{ height: 5, background: C.muted, borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${d.aiCode}%`, background: d.aiCode >= 80 ? C.green : d.aiCode >= 70 ? C.amber : C.red, borderRadius: 3 }} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: "50%",
                  background: d.score >= 80 ? C.greenBg : d.score >= 70 ? C.amberBg : C.redBg,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: F.mono, fontSize: 11, fontWeight: 700,
                  color: d.score >= 80 ? C.green : d.score >= 70 ? C.amber : C.red,
                }}>
                  {d.score}
                </div>
              </div>
            </div>
            {i < devImpact.length - 1 && <Divider />}
          </div>
        ))}
      </div>
      {/* Scatter note */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 18px" }}>
        <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 8 }}>Cost vs Output Scatter</div>
        <div style={{ fontFamily: F.body, fontSize: 12, color: C.sub }}>
          Scatter plot available in full build — shows each developer as a dot plotted by cost per ticket (x) vs tickets closed (y).
          Top-right quadrant = high output, low cost. Bottom-left = needs attention.
          Developer dots are anonymous to peers; names visible only to org admin and team lead.
        </div>
      </div>
    </div>
  );
}

/* ─── Tab: How AI Is Used ────────────────────────────────── */
function TabUsage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {/* Mode breakdown */}
        <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
          <div style={{ padding: "14px 18px 10px" }}>
            <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Session Mode Breakdown</div>
            <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>How developers use AI tools</div>
          </div>
          <Divider />
          <div style={{ padding: "14px 18px" }}>
            {modeData.map((m, i) => (
              <div key={i} style={{ marginBottom: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                  <span style={{ fontFamily: F.body, fontSize: 12, color: C.text }}>{m.mode} mode</span>
                  <span style={{ fontFamily: F.mono, fontSize: 12, fontWeight: 600, color: m.color }}>{m.pct}%</span>
                </div>
                <div style={{ height: 5, background: C.muted, borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${m.pct}%`, background: m.color, borderRadius: 3, opacity: 0.8 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
        {/* Model usage */}
        <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
          <div style={{ padding: "14px 18px 10px" }}>
            <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Model Usage</div>
            <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>Sessions per model · last 30 days</div>
          </div>
          <Divider />
          <div style={{ padding: "6px 0" }}>
            {modelUsage.map((m, i) => (
              <div key={i}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 60px 120px", gap: 10, padding: "9px 18px", alignItems: "center" }}>
                  <span style={{ fontFamily: F.mono, fontSize: 11, color: C.text }}>{m.model}</span>
                  <span style={{ fontFamily: F.mono, fontSize: 11, color: C.sub }}>{m.sessions}</span>
                  <div style={{ height: 5, background: C.muted, borderRadius: 3, overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${(m.sessions / 412) * 100}%`, background: C.accent, borderRadius: 3, opacity: 0.6 }} />
                  </div>
                </div>
                {i < modelUsage.length - 1 && <Divider />}
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* Session length distribution */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px 10px" }}>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Session Length Distribution</div>
          <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>Shorter sessions = lighter tasks · Sessions over 90min without a commit trigger hallucination watch</div>
        </div>
        <Divider />
        <div style={{ padding: "12px 8px 8px" }}>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={sessionLen} margin={{ top: 4, right: 16, bottom: 0, left: -8 }}>
              <XAxis dataKey="range" tick={{ fontSize: 11, fill: C.sub, fontFamily: F.body }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: C.sub, fontFamily: F.body }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: C.surface, border: `1px solid ${C.borderHi}`, borderRadius: 6, fontFamily: F.mono, fontSize: 11 }}
                labelStyle={{ color: C.sub }} itemStyle={{ color: C.accent }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {sessionLen.map((_, i) => (
                  <Cell key={i} fill={i === sessionLen.length - 1 ? C.amber : C.accent} fillOpacity={i === sessionLen.length - 1 ? 0.7 : 0.5} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

/* ─── Tab: Features ──────────────────────────────────────── */
function TabFeatures() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Treemap-style feature blocks */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 18px 10px" }}>
        <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 4 }}>Feature Cost Map</div>
        <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginBottom: 14 }}>Block size = AI cost · Block color = ROI signal</div>
        <div style={{ display: "grid", gridTemplateColumns: "3fr 2.7fr 2.4fr", gridTemplateRows: "80px 60px", gap: 8 }}>
          {spendByFeature.slice(0, 5).map((f, i) => {
            const isNeg = f.roi < 0;
            return (
              <div key={i} style={{
                background: isNeg ? "rgba(255,69,69,0.08)" : "rgba(0,212,255,0.06)",
                border: `1px solid ${isNeg ? "rgba(255,69,69,0.2)" : "rgba(0,212,255,0.15)"}`,
                borderRadius: 8, padding: "10px 12px",
                display: "flex", flexDirection: "column", justifyContent: "space-between",
                cursor: "pointer",
              }}>
                <div style={{ fontFamily: F.body, fontSize: 11, color: C.text, fontWeight: 500 }}>{f.feature}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                  <span style={{ fontFamily: F.mono, fontSize: 13, fontWeight: 700, color: C.warm }}>${(f.cost / 1000).toFixed(1)}k</span>
                  <span style={{ fontFamily: F.mono, fontSize: 11, fontWeight: 600, color: isNeg ? C.red : C.green }}>
                    {isNeg ? "" : "+"}{f.roi}x
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {/* Full table same as Summary but in Features tab */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px 10px" }}>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>All Features</div>
          <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>Click any row to drill into sprint sessions for that feature</div>
        </div>
        <Divider />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 60px 200px 80px", gap: 12, padding: "7px 18px" }}>
          {["Feature", "Cost", "LOC", "ROI", "Signal"].map(h => (
            <span key={h} style={{ fontFamily: F.body, fontSize: 10, color: C.sub, textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>{h}</span>
          ))}
        </div>
        <Divider />
        {spendByFeature.map((f, i) => {
          const isNeg = f.roi < 0;
          const barW = Math.min(Math.abs(f.roi) / 5.5 * 100, 100);
          return (
            <div key={i}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 60px 200px 80px", gap: 12, padding: "11px 18px", alignItems: "center", cursor: "pointer" }}>
                <div>
                  <div style={{ fontFamily: F.body, fontSize: 12, color: C.text }}>{f.feature}</div>
                  <div style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>{f.epic}</div>
                </div>
                <span style={{ fontFamily: F.mono, fontSize: 12, color: C.warm }}>${(f.cost / 1000).toFixed(1)}k</span>
                <span style={{ fontFamily: F.mono, fontSize: 11, color: C.sub }}>{f.loc}</span>
                <div style={{ height: 6, background: C.muted, borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${barW}%`, background: isNeg ? C.red : C.accent, borderRadius: 3, opacity: 0.7 }} />
                </div>
                <Tag color={isNeg ? C.red : C.green} bg={isNeg ? C.redBg : C.greenBg}>{isNeg ? "" : "+"}{f.roi}x</Tag>
              </div>
              {i < spendByFeature.length - 1 && <Divider />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Tab: Activity ──────────────────────────────────────── */
function TabActivity() {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const hours = Array.from({ length: 12 }, (_, i) => `${8 + i}:00`);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Activity heatmap */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px 10px" }}>
          <div style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.text }}>Session Activity Heatmap</div>
          <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginTop: 2 }}>Sessions by day and hour · darker = more sessions</div>
        </div>
        <Divider />
        <div style={{ padding: "14px 18px" }}>
          {/* Hour labels */}
          <div style={{ display: "grid", gridTemplateColumns: "40px repeat(12, 1fr)", gap: 4, marginBottom: 4 }}>
            <div />
            {hours.map(h => (
              <span key={h} style={{ fontFamily: F.mono, fontSize: 8, color: C.sub, textAlign: "center" }}>{h}</span>
            ))}
          </div>
          {days.map(day => (
            <div key={day} style={{ display: "grid", gridTemplateColumns: "40px repeat(12, 1fr)", gap: 4, marginBottom: 4 }}>
              <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub, display: "flex", alignItems: "center" }}>{day}</span>
              {hours.map((h, hi) => {
                const val = Math.floor(Math.random() * 12);
                const opacity = val / 12 * 0.85 + 0.05;
                const isWeekend = day === "Sat" || day === "Sun";
                return (
                  <div key={h} title={`${day} ${h}: ${val} sessions`} style={{
                    height: 18, borderRadius: 3,
                    background: isWeekend ? `rgba(90,90,90,${opacity * 0.5})` : `rgba(0,212,255,${opacity})`,
                    cursor: "pointer",
                  }} />
                );
              })}
            </div>
          ))}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
            <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>Less</span>
            {[0.05, 0.2, 0.4, 0.6, 0.85].map((o, i) => (
              <div key={i} style={{ width: 14, height: 14, borderRadius: 2, background: `rgba(0,212,255,${o})` }} />
            ))}
            <span style={{ fontFamily: F.body, fontSize: 10, color: C.sub }}>More</span>
          </div>
        </div>
      </div>
      {/* Peak usage note */}
      <div style={{
        background: C.accentBg, border: `1px solid rgba(0,212,255,0.15)`,
        borderRadius: 10, padding: "14px 18px",
        display: "flex", gap: 12, alignItems: "flex-start",
      }}>
        <Zap size={16} color={C.accent} style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <div style={{ fontFamily: F.body, fontSize: 13, color: C.text, fontWeight: 500, marginBottom: 4 }}>
            Peak AI usage: Tuesday–Thursday, 10am–3pm
          </div>
          <div style={{ fontFamily: F.body, fontSize: 12, color: C.sub }}>
            Your team's highest-value AI sessions happen mid-week mornings. Weekend and late-night sessions show significantly lower code acceptance rates — consider coaching developers on when AI tools are most effective.
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Root ────────────────────────────────────────────────── */
const TABS = ["Summary", "Developer Impact", "How AI Is Used", "Features", "Activity"] as const;
type Tab = typeof TABS[number];

export default function ROIView() {
  const [activeTab, setActiveTab] = useState<Tab>("Summary");

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
        button { outline: none; }
      `}</style>
      <div style={{
        minHeight: "100vh", background: C.bg,
        fontFamily: F.body, color: C.text,
      }}>
        {/* Page header */}
        <div style={{
          borderBottom: `1px solid ${C.border}`,
          padding: "18px 28px 0",
          background: C.bg,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
            <div>
              <div style={{ fontFamily: F.body, fontSize: 11, color: C.sub, marginBottom: 4 }}>
                Insights · ROI
              </div>
              <h1 style={{ fontFamily: F.ui, fontSize: 22, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>
                AI ROI Intelligence
              </h1>
              <div style={{ fontFamily: F.body, fontSize: 12, color: C.sub, marginTop: 4 }}>
                Connect AI tool spend, time saved, and shipped value into a single number you can defend to finance
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button style={{
                background: "none", border: `1px solid ${C.border}`,
                borderRadius: 7, padding: "7px 14px", cursor: "pointer",
                fontFamily: F.body, fontSize: 12, color: C.sub,
                display: "flex", alignItems: "center", gap: 6,
              }}>
                Last 90 days <ChevronDown size={12} />
              </button>
              <button style={{
                background: C.accentBg, border: `1px solid rgba(0,212,255,0.3)`,
                borderRadius: 7, padding: "7px 14px", cursor: "pointer",
                fontFamily: F.body, fontSize: 12, color: C.accent,
                display: "flex", alignItems: "center", gap: 6,
              }}>
                <Download size={12} /> Export to PDF
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div style={{ display: "flex", gap: 0 }}>
            {TABS.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  fontFamily: F.body, fontSize: 13, fontWeight: activeTab === tab ? 500 : 400,
                  color: activeTab === tab ? C.text : C.sub,
                  padding: "10px 18px",
                  borderBottom: activeTab === tab ? `2px solid ${C.accent}` : "2px solid transparent",
                  transition: "color .15s, border-color .15s",
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div style={{ padding: "22px 28px" }}>
          {activeTab === "Summary"          && <TabSummary />}
          {activeTab === "Developer Impact" && <TabDevImpact />}
          {activeTab === "How AI Is Used"   && <TabUsage />}
          {activeTab === "Features"         && <TabFeatures />}
          {activeTab === "Activity"         && <TabActivity />}
        </div>
      </div>
    </>
  );
}

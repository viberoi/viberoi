/**
 * S-01 Team Dashboard
 * The primary landing screen for Engineering Managers and Tech Leads.
 * Shows AI coding intelligence at a glance — cost, quality, adoption, tools.
 *
 * Dependencies: recharts, lucide-react
 * Fonts: Outfit (headings), DM Sans (body), JetBrains Mono (data)
 */

import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip,
  PieChart, Pie, Cell, BarChart, Bar,
} from "recharts";
import {
  LayoutDashboard, TrendingUp, DollarSign, Users, GitBranch,
  Bell, ChevronDown, AlertTriangle, ArrowUpRight, ArrowDownRight,
  Activity, GitPullRequest, Settings, Shield, X, Cpu, BarChart2,
  Eye, GitCommit, ChevronRight, Circle,
} from "lucide-react";

/* ─── Design Tokens ────────────────────────────────────────────────────── */
const C = {
  bg:         "#070B16",
  bgCard:     "#0C1120",
  bgSidebar:  "#080D1A",
  bgHover:    "#111829",
  bgSelected: "rgba(45,212,191,0.08)",
  accent:     "#2DD4BF",
  accentBg:   "rgba(45,212,191,0.1)",
  purple:     "#818CF8",
  purpleBg:   "rgba(129,140,248,0.1)",
  orange:     "#FB923C",
  orangeBg:   "rgba(251,146,60,0.1)",
  teal2:      "#34D399",
  teal2Bg:    "rgba(52,211,153,0.1)",
  green:      "#10B981",
  greenBg:    "rgba(16,185,129,0.12)",
  amber:      "#F59E0B",
  amberBg:    "rgba(245,158,11,0.12)",
  red:        "#EF4444",
  redBg:      "rgba(239,68,68,0.12)",
  text:       "#E8EDF5",
  textSub:    "#6B7280",
  textMuted:  "#374151",
  border:     "rgba(255,255,255,0.06)",
  borderBrt:  "rgba(255,255,255,0.12)",
} as const;

const FONTS = {
  heading: "'Outfit', sans-serif",
  body:    "'DM Sans', sans-serif",
  mono:    "'JetBrains Mono', monospace",
} as const;

/* ─── Mock Data ─────────────────────────────────────────────────────────── */
const usageData = [
  { w: "W1", v: 62 }, { w: "W2", v: 71 }, { w: "W3", v: 58 },
  { w: "W4", v: 83 }, { w: "W5", v: 76 }, { w: "W6", v: 89 },
  { w: "W7", v: 74 }, { w: "W8", v: 91 },
];

const toolsData = [
  { name: "Cursor",      value: 52, color: C.accent  },
  { name: "Claude Code", value: 22, color: C.purple  },
  { name: "Kiro",        value: 14, color: C.orange  },
  { name: "Copilot",     value: 12, color: C.teal2   },
];

const prSizeData = [
  { d: "W1", v: 820 }, { d: "W2", v: 1240 }, { d: "W3", v: 960 },
  { d: "W4", v: 1580 }, { d: "W5", v: 1320 }, { d: "W6", v: 1890 },
  { d: "W7", v: 1640 }, { d: "W8", v: 2100 },
];

const commitsData = [
  { d: "Mon", v: 3.2 }, { d: "Tue", v: 4.8 }, { d: "Wed", v: 3.9 },
  { d: "Thu", v: 5.4 }, { d: "Fri", v: 4.1 }, { d: "Sat", v: 1.2 },
  { d: "Sun", v: 0.8 },
];

const sparklines = {
  contribution: [74,78,71,82,79,83,80,82].map((v, i) => ({ i, v })),
  lift:         [1.2,1.3,1.1,1.4,1.35,1.44,1.38,1.44].map((v, i) => ({ i, v })),
  quality:      [80,78,82,79,77,75,74,76].map((v, i) => ({ i, v })),
  spend:        [980,1050,1120,1180,1090,1150,1200,1247].map((v, i) => ({ i, v })),
};

/* ─── Status Badge ──────────────────────────────────────────────────────── */
function StatusBadge({ status }: { status: "HEALTHY" | "WATCH" | "AT RISK" }) {
  const cfg = {
    HEALTHY:  { bg: C.greenBg,  text: C.green,  dot: C.green  },
    WATCH:    { bg: C.amberBg,  text: C.amber,  dot: C.amber  },
    "AT RISK":{ bg: C.redBg,    text: C.red,    dot: C.red    },
  }[status];

  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "3px 9px", borderRadius: 20,
      background: cfg.bg, color: cfg.text,
      fontSize: 10, fontWeight: 600, fontFamily: FONTS.body,
      letterSpacing: "0.06em",
    }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: cfg.dot }} />
      {status}
    </span>
  );
}

/* ─── Mini Sparkline ────────────────────────────────────────────────────── */
function MiniSparkline({ data, color }: { data: {i:number;v:number}[], color: string }) {
  return (
    <ResponsiveContainer width={80} height={32}>
      <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
        <defs>
          <linearGradient id={`sg-${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone" dataKey="v" stroke={color} strokeWidth={1.5}
          fill={`url(#sg-${color.replace("#","")})`} dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ─── KPI Card ──────────────────────────────────────────────────────────── */
interface KPICardProps {
  label: string;
  value: string;
  trend: string;
  trendUp: boolean;
  status?: "HEALTHY" | "WATCH" | "AT RISK";
  sparklineData: {i:number;v:number}[];
  sparkColor: string;
  icon: React.ComponentType<{size?:number;color?:string}>;
}

function KPICard({ label, value, trend, trendUp, status, sparklineData, sparkColor, icon: Icon }: KPICardProps) {
  const [hov, setHov] = useState(false);

  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: C.bgCard,
        border: `1px solid ${hov ? C.borderBrt : C.border}`,
        borderRadius: 12,
        padding: "20px 20px 16px",
        display: "flex", flexDirection: "column", gap: 12,
        transition: "border-color 0.15s ease, transform 0.15s ease",
        transform: hov ? "translateY(-1px)" : "none",
        cursor: "default",
      }}
    >
      {/* top row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: `${sparkColor}15`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Icon size={14} color={sparkColor} />
          </div>
          <span style={{ fontFamily: FONTS.body, fontSize: 12, color: C.textSub, fontWeight: 500 }}>
            {label}
          </span>
        </div>
        {status && <StatusBadge status={status} />}
      </div>

      {/* value + sparkline */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div style={{
            fontFamily: FONTS.mono, fontSize: 30, fontWeight: 600,
            color: C.text, lineHeight: 1, letterSpacing: "-0.02em",
          }}>
            {value}
          </div>
          <div style={{
            display: "flex", alignItems: "center", gap: 4, marginTop: 6,
            fontFamily: FONTS.body, fontSize: 11, color: trendUp ? C.green : C.red,
          }}>
            {trendUp
              ? <ArrowUpRight size={12} color={C.green} />
              : <ArrowDownRight size={12} color={C.red} />}
            {trend} vs last period
          </div>
        </div>
        <MiniSparkline data={sparklineData} color={sparkColor} />
      </div>
    </div>
  );
}

/* ─── Custom Tooltip ────────────────────────────────────────────────────── */
function ChartTooltip({ active, payload, label, unit = "" }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: C.bgHover, border: `1px solid ${C.borderBrt}`,
      borderRadius: 8, padding: "8px 12px",
      fontFamily: FONTS.body, fontSize: 12, color: C.text,
    }}>
      <div style={{ color: C.textSub, marginBottom: 3 }}>{label}</div>
      <div style={{ fontFamily: FONTS.mono, fontSize: 14, color: C.accent, fontWeight: 600 }}>
        {payload[0].value}{unit}
      </div>
    </div>
  );
}

/* ─── Sidebar Nav Item ──────────────────────────────────────────────────── */
function NavItem({
  icon: Icon, label, active, badge, collapsed,
}: {
  icon: React.ComponentType<{size?:number;color?:string}>;
  label: string; active?: boolean; badge?: number; collapsed?: boolean;
}) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", alignItems: "center",
        gap: collapsed ? 0 : 10,
        padding: collapsed ? "9px 0" : "9px 12px",
        justifyContent: collapsed ? "center" : "flex-start",
        borderRadius: 8,
        background: active ? C.bgSelected : hov ? "rgba(255,255,255,0.03)" : "transparent",
        borderLeft: active ? `2px solid ${C.accent}` : "2px solid transparent",
        cursor: "pointer", transition: "all 0.12s ease",
        position: "relative",
      }}
    >
      <Icon size={15} color={active ? C.accent : hov ? C.text : C.textSub} />
      {!collapsed && (
        <span style={{
          fontFamily: FONTS.body, fontSize: 13, fontWeight: active ? 500 : 400,
          color: active ? C.text : hov ? C.text : C.textSub,
          flex: 1, transition: "color 0.12s",
        }}>
          {label}
        </span>
      )}
      {!collapsed && badge && (
        <span style={{
          background: C.redBg, color: C.red,
          fontSize: 10, fontWeight: 700, fontFamily: FONTS.mono,
          padding: "1px 6px", borderRadius: 10,
        }}>
          {badge}
        </span>
      )}
      {collapsed && badge && (
        <span style={{
          position: "absolute", top: 4, right: 4,
          width: 7, height: 7, borderRadius: "50%", background: C.red,
        }} />
      )}
    </div>
  );
}

/* ─── Sidebar ───────────────────────────────────────────────────────────── */
function Sidebar({ collapsed }: { collapsed: boolean }) {
  const w = collapsed ? 60 : 240;

  const sections = [
    {
      title: "Insights",
      items: [
        { icon: LayoutDashboard, label: "Team Dashboard",   active: true  },
        { icon: TrendingUp,      label: "AI Insights"                     },
        { icon: DollarSign,      label: "ROI"                             },
        { icon: Cpu,             label: "Agentic Insights"                },
        { icon: BarChart2,       label: "General Metrics"                 },
        { icon: Activity,        label: "Capacity Overview"               },
      ],
    },
    {
      title: "Team",
      items: [
        { icon: Eye,   label: "My Activity" },
        { icon: Users, label: "People"      },
      ],
    },
    {
      title: "Management",
      items: [
        { icon: GitBranch,     label: "Unknown Queue", badge: 12 },
        { icon: AlertTriangle, label: "Alerts",        badge: 2  },
      ],
    },
  ];

  return (
    <div style={{
      width: w, minWidth: w, height: "100vh",
      background: C.bgSidebar,
      borderRight: `1px solid ${C.border}`,
      display: "flex", flexDirection: "column",
      transition: "width 0.2s ease",
      overflow: "hidden",
    }}>
      {/* Logo */}
      <div style={{
        height: 56, display: "flex", alignItems: "center",
        padding: collapsed ? "0 18px" : "0 20px",
        borderBottom: `1px solid ${C.border}`,
        gap: 10,
      }}>
        <div style={{
          width: 26, height: 26, borderRadius: 7,
          background: C.accentBg, border: `1px solid ${C.accent}40`,
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0,
        }}>
          <Shield size={14} color={C.accent} />
        </div>
        {!collapsed && (
          <span style={{
            fontFamily: FONTS.heading, fontWeight: 700, fontSize: 15,
            color: C.text, letterSpacing: "-0.02em",
          }}>
            [Product]
          </span>
        )}
      </div>

      {/* Nav */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 10px" }}>
        {sections.map((sec, si) => (
          <div key={si} style={{ marginBottom: 4 }}>
            {!collapsed && (
              <div style={{
                fontFamily: FONTS.body, fontSize: 10, fontWeight: 600,
                color: C.textMuted, letterSpacing: "0.1em",
                padding: "10px 12px 4px",
                textTransform: "uppercase",
              }}>
                {sec.title}
              </div>
            )}
            {collapsed && si > 0 && (
              <div style={{ height: 1, background: C.border, margin: "8px 10px" }} />
            )}
            {sec.items.map((item, ii) => (
              <NavItem
                key={ii}
                icon={item.icon}
                label={item.label}
                active={item.active}
                badge={item.badge}
                collapsed={collapsed}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Bottom */}
      <div style={{ padding: "12px 10px", borderTop: `1px solid ${C.border}` }}>
        <NavItem icon={Settings} label="Settings" collapsed={collapsed} />
        {!collapsed && (
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "10px 12px 4px",
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: C.accentBg,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontFamily: FONTS.mono, fontSize: 11, fontWeight: 600, color: C.accent,
            }}>
              AK
            </div>
            <div>
              <div style={{ fontFamily: FONTS.body, fontSize: 12, color: C.text, fontWeight: 500 }}>
                Adnan Khan
              </div>
              <div style={{ fontFamily: FONTS.body, fontSize: 10, color: C.textSub }}>
                Org Admin
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Top Bar ───────────────────────────────────────────────────────────── */
function TopBar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  return (
    <div style={{
      height: 56, display: "flex", alignItems: "center",
      justifyContent: "space-between",
      padding: "0 24px",
      borderBottom: `1px solid ${C.border}`,
      background: C.bg,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <h1 style={{
          fontFamily: FONTS.heading, fontSize: 18, fontWeight: 600,
          color: C.text, letterSpacing: "-0.02em",
        }}>
          Team Dashboard
        </h1>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* Date range */}
        <button style={{
          display: "flex", alignItems: "center", gap: 7,
          background: C.bgCard, border: `1px solid ${C.border}`,
          borderRadius: 8, padding: "6px 12px", cursor: "pointer",
          fontFamily: FONTS.body, fontSize: 12, color: C.text,
        }}>
          Last 30 days <ChevronDown size={13} color={C.textSub} />
        </button>

        {/* Team filter */}
        <button style={{
          display: "flex", alignItems: "center", gap: 7,
          background: C.bgCard, border: `1px solid ${C.border}`,
          borderRadius: 8, padding: "6px 12px", cursor: "pointer",
          fontFamily: FONTS.body, fontSize: 12, color: C.text,
        }}>
          All teams <ChevronDown size={13} color={C.textSub} />
        </button>

        {/* Bell */}
        <div style={{ position: "relative", cursor: "pointer" }}>
          <div style={{
            width: 34, height: 34, borderRadius: 8,
            background: C.bgCard, border: `1px solid ${C.border}`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Bell size={15} color={C.textSub} />
          </div>
          <span style={{
            position: "absolute", top: 6, right: 7,
            width: 7, height: 7, borderRadius: "50%", background: C.red,
          }} />
        </div>

        {/* Avatar */}
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          background: C.accentBg, border: `1px solid ${C.accent}40`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: FONTS.mono, fontSize: 10, fontWeight: 600, color: C.accent,
          cursor: "pointer",
        }}>
          AK
        </div>
      </div>
    </div>
  );
}

/* ─── Hallucination Alert Banner ────────────────────────────────────────── */
function AlertBanner({ onClose }: { onClose: () => void }) {
  return (
    <div style={{
      background: `${C.amber}12`,
      border: `1px solid ${C.amber}30`,
      borderRadius: 10, padding: "10px 16px",
      display: "flex", alignItems: "center",
      justifyContent: "space-between", marginBottom: 20,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <AlertTriangle size={15} color={C.amber} />
        <span style={{
          fontFamily: FONTS.body, fontSize: 13, color: C.text, fontWeight: 500,
        }}>
          2 developers may be stuck in hallucination loops this week
        </span>
        <span style={{ color: C.textSub, fontSize: 13 }}>—</span>
        <span style={{
          fontFamily: FONTS.body, fontSize: 13, color: C.accent,
          cursor: "pointer", display: "flex", alignItems: "center", gap: 4,
        }}>
          View alerts <ChevronRight size={12} color={C.accent} />
        </span>
      </div>
      <button
        onClick={onClose}
        style={{ background: "none", border: "none", cursor: "pointer", padding: 2 }}
      >
        <X size={14} color={C.textSub} />
      </button>
    </div>
  );
}

/* ─── Section Header ────────────────────────────────────────────────────── */
function SectionHeader({ title, badge, badgeStatus }: {
  title: string;
  badge?: string;
  badgeStatus?: "HEALTHY" | "WATCH" | "AT RISK";
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
      <span style={{
        fontFamily: FONTS.heading, fontSize: 14, fontWeight: 600,
        color: C.text, letterSpacing: "-0.01em",
      }}>
        {title}
      </span>
      {badge && badgeStatus && <StatusBadge status={badgeStatus} />}
      <span style={{ fontFamily: FONTS.body, fontSize: 11, color: C.textSub, marginTop: 1 }}>
        Last 30 days
      </span>
    </div>
  );
}

/* ─── Main Dashboard ────────────────────────────────────────────────────── */
export default function TeamDashboard() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showAlert, setShowAlert] = useState(true);

  return (
    <>
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { background: ${C.bg}; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 2px; }
      `}</style>

      <div style={{
        display: "flex", height: "100vh", background: C.bg,
        fontFamily: FONTS.body, color: C.text, overflow: "hidden",
      }}>
        {/* Sidebar */}
        <Sidebar collapsed={sidebarCollapsed} />

        {/* Main */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <TopBar onToggleSidebar={() => setSidebarCollapsed(p => !p)} />

          {/* Content */}
          <div style={{
            flex: 1, overflowY: "auto",
            padding: "24px 28px",
          }}>
            {/* Alert banner */}
            {showAlert && <AlertBanner onClose={() => setShowAlert(false)} />}

            {/* KPI Row */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 14, marginBottom: 20,
            }}>
              <KPICard
                label="AI Code Contribution"
                value="82.0%"
                trend="+12%"
                trendUp
                status="HEALTHY"
                sparklineData={sparklines.contribution}
                sparkColor={C.accent}
                icon={GitCommit}
              />
              <KPICard
                label="AI Productivity Lift"
                value="1.44x"
                trend="+0.2x"
                trendUp
                status="WATCH"
                sparklineData={sparklines.lift}
                sparkColor={C.purple}
                icon={TrendingUp}
              />
              <KPICard
                label="AI Code Quality"
                value="76.0%"
                trend="-2%"
                trendUp={false}
                status="HEALTHY"
                sparklineData={sparklines.quality}
                sparkColor={C.orange}
                icon={Shield}
              />
              <KPICard
                label="Total AI Spend"
                value="$1,247"
                trend="+$98"
                trendUp
                sparklineData={sparklines.spend}
                sparkColor={C.teal2}
                icon={DollarSign}
              />
            </div>

            {/* Charts row */}
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 380px",
              gap: 14, marginBottom: 20,
            }}>
              {/* AI Usage Chart */}
              <div style={{
                background: C.bgCard,
                border: `1px solid ${C.border}`,
                borderRadius: 12, padding: "20px 20px 12px",
              }}>
                <SectionHeader title="AI Usage Percentage" badge="GOOD" badgeStatus="HEALTHY" />
                <div style={{ fontSize: 11, color: C.textSub, marginBottom: 12, fontFamily: FONTS.body }}>
                  % of active AI users per week
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={usageData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <defs>
                      <linearGradient id="usageGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor={C.accent} stopOpacity={0.25} />
                        <stop offset="95%" stopColor={C.accent} stopOpacity={0}    />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="w" tick={{ fontSize: 11, fill: C.textSub, fontFamily: FONTS.body }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: C.textSub, fontFamily: FONTS.body }} axisLine={false} tickLine={false} domain={[0,100]} tickFormatter={v => `${v}%`} />
                    <Tooltip content={<ChartTooltip unit="%" />} />
                    <Area
                      type="monotone" dataKey="v" name="Usage"
                      stroke={C.accent} strokeWidth={2}
                      fill="url(#usageGrad)" dot={false}
                      activeDot={{ r: 4, fill: C.accent, strokeWidth: 0 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
                <div style={{
                  marginTop: 8, padding: "10px 0 0",
                  borderTop: `1px solid ${C.border}`,
                  display: "flex", gap: 6, flexWrap: "wrap",
                }}>
                  <span style={{ fontSize: 11, color: C.textSub, fontFamily: FONTS.body }}>
                    Identify teams that need extra AI onboarding to keep adoption climbing week over week.
                  </span>
                  <span style={{
                    fontSize: 11, color: C.accent, fontFamily: FONTS.body,
                    cursor: "pointer", display: "flex", alignItems: "center", gap: 2, whiteSpace: "nowrap",
                  }}>
                    View by team <ChevronRight size={11} color={C.accent} />
                  </span>
                </div>
              </div>

              {/* Tools Breakdown */}
              <div style={{
                background: C.bgCard,
                border: `1px solid ${C.border}`,
                borderRadius: 12, padding: "20px",
              }}>
                <SectionHeader title="AI Tools Breakdown" />
                <div style={{ fontSize: 11, color: C.textSub, marginBottom: 4, fontFamily: FONTS.body }}>
                  Last 30 days
                </div>

                <div style={{ display: "flex", justifyContent: "center", margin: "8px 0" }}>
                  <PieChart width={160} height={160}>
                    <Pie
                      data={toolsData} cx={76} cy={76} innerRadius={48} outerRadius={72}
                      paddingAngle={3} dataKey="value" stroke="none"
                    >
                      {toolsData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </div>

                {/* Legend */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {toolsData.map((t, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ width: 8, height: 8, borderRadius: 2, background: t.color, flexShrink: 0 }} />
                        <span style={{ fontFamily: FONTS.body, fontSize: 12, color: C.textSub }}>{t.name}</span>
                      </div>
                      <span style={{ fontFamily: FONTS.mono, fontSize: 12, fontWeight: 600, color: C.text }}>
                        {t.value}%
                      </span>
                    </div>
                  ))}
                </div>

                <div style={{
                  marginTop: 12, padding: "10px 0 0",
                  borderTop: `1px solid ${C.border}`,
                }}>
                  <span style={{ fontSize: 11, color: C.textSub, fontFamily: FONTS.body }}>
                    Evaluate vendor mix to avoid single-tool dependency.
                  </span>
                </div>
              </div>
            </div>

            {/* Bottom row */}
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 1fr",
              gap: 14,
            }}>
              {/* AI PR Size */}
              <div style={{
                background: C.bgCard,
                border: `1px solid ${C.redBg}`,
                borderRadius: 12, padding: "20px 20px 12px",
              }}>
                <SectionHeader title="AI PR Size" badge="AT RISK" badgeStatus="AT RISK" />
                <div style={{ fontSize: 11, color: C.textSub, marginBottom: 12, fontFamily: FONTS.body }}>
                  Avg lines of code of AI-written PRs
                </div>
                <ResponsiveContainer width="100%" height={130}>
                  <BarChart data={prSizeData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <XAxis dataKey="d" tick={{ fontSize: 10, fill: C.textSub, fontFamily: FONTS.body }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: C.textSub, fontFamily: FONTS.body }} axisLine={false} tickLine={false} />
                    <Tooltip content={<ChartTooltip unit=" LOC" />} />
                    <Bar dataKey="v" radius={[3,3,0,0]}>
                      {prSizeData.map((entry, i) => (
                        <Cell key={i} fill={entry.v > 1500 ? C.red : C.redBg} fillOpacity={entry.v > 1500 ? 1 : 0.6} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div style={{
                  marginTop: 8, padding: "8px 0 0",
                  borderTop: `1px solid ${C.border}`,
                }}>
                  <span style={{ fontSize: 11, color: C.red, fontFamily: FONTS.body }}>
                    ⚠ PRs exceeding 1,500 LOC are difficult to review properly. Average this week: 2,100 LOC.
                  </span>
                </div>
              </div>

              {/* AI Commits per Dev */}
              <div style={{
                background: C.bgCard,
                border: `1px solid ${C.border}`,
                borderRadius: 12, padding: "20px 20px 12px",
              }}>
                <SectionHeader title="AI Commits per Dev per Day" badge="WATCH" badgeStatus="WATCH" />
                <div style={{ fontSize: 11, color: C.textSub, marginBottom: 12, fontFamily: FONTS.body }}>
                  AI commits per developer this week
                </div>
                <ResponsiveContainer width="100%" height={130}>
                  <BarChart data={commitsData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <XAxis dataKey="d" tick={{ fontSize: 10, fill: C.textSub, fontFamily: FONTS.body }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: C.textSub, fontFamily: FONTS.body }} axisLine={false} tickLine={false} />
                    <Tooltip content={<ChartTooltip unit=" commits" />} />
                    <Bar dataKey="v" fill={C.accent} fillOpacity={0.7} radius={[3,3,0,0]}>
                      {commitsData.map((entry, i) => (
                        <Cell key={i} fill={C.accent} fillOpacity={entry.v < 2 ? 0.25 : 0.7} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div style={{
                  marginTop: 8, padding: "8px 0 0",
                  borderTop: `1px solid ${C.border}`,
                }}>
                  <span style={{ fontSize: 11, color: C.textSub, fontFamily: FONTS.body }}>
                    Weekend activity low as expected. Mid-week peak at 5.4 commits/dev/day.
                  </span>
                </div>
              </div>
            </div>

          </div>{/* /content */}
        </div>{/* /main */}
      </div>
    </>
  );
}

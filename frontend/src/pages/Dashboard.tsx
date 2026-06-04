import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AreaChart, Card, Metric, Text, Title } from "@tremor/react";
import { Info } from "lucide-react";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const WINDOWS = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

type Metric = "cost" | "sessions" | "tokens";

function fmtCurrency(s: string | number): string {
  const n = typeof s === "string" ? parseFloat(s) : s;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(n || 0);
}

function fmtInt(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

function fmtMinutes(seconds: number | null): string {
  if (seconds === null) return "—";
  return `${Math.round(seconds / 60)} min`;
}

export function Dashboard() {
  const { user } = useAuth();
  const canSeeTeam = user?.role === "OrgAdmin" || user?.role === "TeamLead";
  const [windowDays, setWindowDays] = useState(30);
  const [metric, setMetric] = useState<Metric>("cost");

  const snapshot = useQuery({
    queryKey: ["kpis", windowDays],
    queryFn: () => api.kpiSnapshot(windowDays),
  });
  const timeseries = useQuery({
    queryKey: ["kpis-timeseries", windowDays],
    queryFn: () => api.kpiTimeseries(windowDays),
  });
  const byDeveloper = useQuery({
    queryKey: ["kpis-by-dev", windowDays],
    queryFn: () => api.kpiByDeveloper(windowDays, 10),
    enabled: canSeeTeam,
  });

  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <Title className="font-ui">Dashboard</Title>
          <Text className="text-viberoi-sub">
            Rolling {windowDays}-day organization KPIs.
          </Text>
        </div>
        <div className="flex items-center gap-1 bg-viberoi-card border border-white/5 rounded-md p-1">
          {WINDOWS.map((w) => (
            <button
              key={w.days}
              onClick={() => setWindowDays(w.days)}
              className={`px-3 py-1 rounded text-xs ${
                windowDays === w.days
                  ? "bg-viberoi-accent/15 text-viberoi-accent"
                  : "text-viberoi-sub hover:text-viberoi-text"
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {snapshot.isLoading && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text>Loading…</Text>
        </Card>
      )}
      {snapshot.isError && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text className="text-red-400">
            Failed to load KPIs: {(snapshot.error as Error).message}
          </Text>
        </Card>
      )}

      {snapshot.data && (
        <>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard
              label="Total sessions"
              value={fmtInt(snapshot.data.total_sessions)}
            />
            <KpiCard
              label="Total cost"
              value={fmtCurrency(snapshot.data.total_cost_usd)}
              hint="API-equivalent — see info."
              tooltip={costTooltip}
            />
            <KpiCard
              label="Active developers"
              value={fmtInt(snapshot.data.active_developers)}
            />
            <KpiCard
              label="Avg session"
              value={fmtMinutes(snapshot.data.avg_session_duration_seconds)}
            />
          </div>

          <Card className="mt-6 bg-viberoi-card border-white/5">
            <div className="flex items-center justify-between mb-3">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Trend
              </Text>
              <div className="flex gap-1">
                {(["cost", "sessions", "tokens"] as Metric[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMetric(m)}
                    className={`px-2 py-1 rounded text-xs ${
                      metric === m
                        ? "bg-viberoi-accent/15 text-viberoi-accent"
                        : "text-viberoi-sub hover:text-viberoi-text"
                    }`}
                  >
                    {m === "cost" ? "$" : m === "sessions" ? "sessions" : "tokens"}
                  </button>
                ))}
              </div>
            </div>
            {timeseries.isLoading ? (
              <Text className="text-viberoi-sub py-12 text-center">
                Loading chart…
              </Text>
            ) : (
              <AreaChart
                data={
                  timeseries.data?.points.map((p) => ({
                    day: new Date(p.day).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    }),
                    [metric]:
                      metric === "cost"
                        ? parseFloat(p.cost_usd)
                        : metric === "sessions"
                        ? p.sessions
                        : p.tokens,
                  })) ?? []
                }
                index="day"
                categories={[metric]}
                colors={["emerald"]}
                showLegend={false}
                showAnimation={true}
                valueFormatter={(n) =>
                  metric === "cost" ? `$${n.toLocaleString()}` : n.toLocaleString()
                }
                className="h-64"
              />
            )}
          </Card>

          {canSeeTeam && (
            <Card className="mt-6 bg-viberoi-card border-white/5 p-0 overflow-hidden">
              <div className="px-6 pt-4 pb-3 flex items-center justify-between">
                <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                  Top developers
                </Text>
                <Text className="text-xs text-viberoi-sub">
                  Last {windowDays} days
                </Text>
              </div>
              <TopDevelopersTable data={byDeveloper.data?.items ?? []} isLoading={byDeveloper.isLoading} />
            </Card>
          )}
        </>
      )}
    </div>
  );
}

const costTooltip = (
  <span>
    Equivalent API cost — what your usage would cost via the Anthropic API
    at public per-token rates. Your actual bill differs if you're on Pro
    ($20/mo), Max, Team, or Enterprise. Useful as a comparable ROI figure
    across tools.
  </span>
);

function KpiCard({
  label,
  value,
  hint,
  tooltip,
}: {
  label: string;
  value: string;
  hint?: string;
  tooltip?: React.ReactNode;
}) {
  return (
    <Card className="bg-viberoi-card border-white/5">
      <div className="flex items-center gap-1.5">
        <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
          {label}
        </Text>
        {tooltip && (
          <span className="group relative">
            <Info size={11} className="text-viberoi-sub cursor-help" />
            <span className="invisible group-hover:visible absolute z-10 left-4 -top-2 w-64 p-2 text-xs bg-viberoi-bg border border-white/10 rounded text-viberoi-text font-normal normal-case tracking-normal">
              {tooltip}
            </span>
          </span>
        )}
      </div>
      <Metric className="font-mono text-viberoi-text">{value}</Metric>
      {hint && (
        <Text className="text-[10px] text-viberoi-sub mt-1">{hint}</Text>
      )}
    </Card>
  );
}

function TopDevelopersTable({
  data,
  isLoading,
}: {
  data: Array<{
    developer_id: string;
    email: string;
    role: string;
    sessions: number;
    tokens: number;
    cost_usd: string;
  }>;
  isLoading: boolean;
}) {
  const nav = useNavigate();
  if (isLoading) {
    return (
      <Text className="text-viberoi-sub py-8 text-center">Loading team…</Text>
    );
  }
  if (data.length === 0) {
    return (
      <Text className="text-viberoi-sub py-8 text-center">
        No team data yet — invite teammates from Settings → Team.
      </Text>
    );
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wider text-viberoi-sub border-b border-white/5">
          <th className="px-6 py-3 font-normal">Email</th>
          <th className="px-6 py-3 font-normal">Role</th>
          <th className="px-6 py-3 font-normal text-right">Sessions</th>
          <th className="px-6 py-3 font-normal text-right">Tokens</th>
          <th className="px-6 py-3 font-normal text-right">Cost</th>
        </tr>
      </thead>
      <tbody>
        {data.map((d) => (
          <tr
            key={d.developer_id}
            className="border-b border-white/5 hover:bg-white/5 cursor-pointer"
            onClick={() => nav(`/sessions?developer=${d.developer_id}`)}
          >
            <td className="px-6 py-3">{d.email}</td>
            <td className="px-6 py-3 text-xs text-viberoi-sub">{d.role}</td>
            <td className="px-6 py-3 text-right font-mono">{d.sessions}</td>
            <td className="px-6 py-3 text-right font-mono">
              {d.tokens.toLocaleString()}
            </td>
            <td className="px-6 py-3 text-right font-mono">
              ${parseFloat(d.cost_usd).toFixed(2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

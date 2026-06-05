import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AreaChart, Card, DonutChart, Metric, Text, Title } from "@tremor/react";
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
  const byTool = useQuery({
    queryKey: ["kpis-by-tool", windowDays],
    queryFn: () => api.kpiByTool(windowDays),
  });
  const byMode = useQuery({
    queryKey: ["kpis-by-mode", windowDays],
    queryFn: () => api.kpiByMode(windowDays),
  });
  const byModel = useQuery({
    queryKey: ["kpis-by-model", windowDays],
    queryFn: () => api.kpiByModel(windowDays),
  });
  const perTicket = useQuery({
    queryKey: ["kpis-per-ticket", windowDays],
    queryFn: () => api.kpiPerTicket(windowDays, 10),
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

          {/* Breakdowns row */}
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs mb-2">
                Tool mix
              </Text>
              <DonutChartCard
                data={byTool.data?.items.map((t) => ({
                  name: t.tool_name,
                  value: parseFloat(t.cost_usd),
                })) ?? []}
                isLoading={byTool.isLoading}
                emptyHint="No sessions yet"
              />
            </Card>
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs mb-2">
                Mode breakdown
              </Text>
              <DonutChartCard
                data={byMode.data?.items.map((m) => ({
                  name: m.mode,
                  value: m.sessions,
                })) ?? []}
                isLoading={byMode.isLoading}
                emptyHint="No mode data"
                valueLabel="sessions"
              />
            </Card>
            <Card className="bg-viberoi-card border-white/5 overflow-hidden p-0">
              <div className="px-4 pt-3 pb-1">
                <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                  Top tickets by AI cost
                </Text>
              </div>
              <PerTicketTable
                data={perTicket.data?.items ?? []}
                isLoading={perTicket.isLoading}
              />
            </Card>
          </div>

          {/* Model usage */}
          <Card className="mt-6 bg-viberoi-card border-white/5 p-0 overflow-hidden">
            <div className="px-6 pt-4 pb-2">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Model usage
              </Text>
            </div>
            <ModelTable
              data={byModel.data?.items ?? []}
              isLoading={byModel.isLoading}
            />
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
    lines_added: number;
    lines_deleted: number;
    commit_count: number;
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
          <th className="px-6 py-3 font-normal text-right">LOC</th>
          <th className="px-6 py-3 font-normal text-right">Commits</th>
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
            <td className="px-6 py-3 text-right font-mono text-xs">
              <span className="text-emerald-400">+{d.lines_added}</span>{" "}
              <span className="text-red-400">-{d.lines_deleted}</span>
            </td>
            <td className="px-6 py-3 text-right font-mono">{d.commit_count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DonutChartCard({
  data,
  isLoading,
  emptyHint,
  valueLabel,
}: {
  data: Array<{ name: string; value: number }>;
  isLoading: boolean;
  emptyHint: string;
  valueLabel?: string;
}) {
  if (isLoading) {
    return <Text className="text-viberoi-sub py-12 text-center">Loading…</Text>;
  }
  if (data.length === 0) {
    return (
      <Text className="text-viberoi-sub py-12 text-center text-xs">
        {emptyHint}
      </Text>
    );
  }
  return (
    <DonutChart
      data={data}
      category="value"
      index="name"
      colors={["emerald", "blue", "violet", "amber", "rose"]}
      valueFormatter={(n: number) =>
        valueLabel ? `${n.toLocaleString()} ${valueLabel}` : `$${n.toFixed(2)}`
      }
      className="h-44"
    />
  );
}

function PerTicketTable({
  data,
  isLoading,
}: {
  data: Array<{ ticket_external_id: string; sessions: number; cost_usd: string }>;
  isLoading: boolean;
}) {
  const nav = useNavigate();
  if (isLoading) {
    return <Text className="text-viberoi-sub py-8 text-center">Loading…</Text>;
  }
  if (data.length === 0) {
    return (
      <Text className="text-viberoi-sub py-8 text-center text-xs">
        No tickets attributed yet
      </Text>
    );
  }
  return (
    <table className="w-full text-sm">
      <tbody>
        {data.map((t) => (
          <tr
            key={t.ticket_external_id}
            className="border-b border-white/5 hover:bg-white/5 cursor-pointer"
            onClick={() => nav(`/sessions?ticket=${t.ticket_external_id}`)}
          >
            <td className="px-4 py-2 font-mono text-xs">
              {t.ticket_external_id}
            </td>
            <td className="px-4 py-2 text-right text-xs text-viberoi-sub">
              {t.sessions}s
            </td>
            <td className="px-4 py-2 text-right font-mono">
              ${parseFloat(t.cost_usd).toFixed(2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ModelTable({
  data,
  isLoading,
}: {
  data: Array<{
    model: string;
    sessions: number;
    input_tokens: number;
    output_tokens: number;
    cost_usd: string;
  }>;
  isLoading: boolean;
}) {
  if (isLoading) {
    return <Text className="text-viberoi-sub py-8 text-center">Loading…</Text>;
  }
  if (data.length === 0) {
    return (
      <Text className="text-viberoi-sub py-8 text-center text-xs">
        No model data yet
      </Text>
    );
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wider text-viberoi-sub border-b border-white/5">
          <th className="px-6 py-3 font-normal">Model</th>
          <th className="px-6 py-3 font-normal text-right">Sessions</th>
          <th className="px-6 py-3 font-normal text-right">Input tokens</th>
          <th className="px-6 py-3 font-normal text-right">Output tokens</th>
          <th className="px-6 py-3 font-normal text-right">Cost</th>
        </tr>
      </thead>
      <tbody>
        {data.map((m) => (
          <tr
            key={m.model}
            className="border-b border-white/5 hover:bg-white/5"
          >
            <td className="px-6 py-3 font-mono text-xs">{m.model}</td>
            <td className="px-6 py-3 text-right font-mono">{m.sessions}</td>
            <td className="px-6 py-3 text-right font-mono">
              {m.input_tokens.toLocaleString()}
            </td>
            <td className="px-6 py-3 text-right font-mono">
              {m.output_tokens.toLocaleString()}
            </td>
            <td className="px-6 py-3 text-right font-mono">
              ${parseFloat(m.cost_usd).toFixed(2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

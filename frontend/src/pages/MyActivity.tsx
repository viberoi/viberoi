/**
 * My Activity — personal dashboard.
 *
 * Per Master spec S-07: every role sees their own data here; admins
 * can also see Dashboard for the org-wide picture. Developers see ONLY
 * this page (no org-wide stats leaked).
 *
 * Backend scopes /me/* hard to ctx.developer_id — even an OrgAdmin's
 * /me/summary returns only their own work.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, DonutChart, Metric, Text, Title } from "@tremor/react";

import { api, type SessionSummary } from "../api/client";

const WINDOWS = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

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

export function MyActivity() {
  const [windowDays, setWindowDays] = useState(30);
  const nav = useNavigate();

  const summary = useQuery({
    queryKey: ["me-summary", windowDays],
    queryFn: () => api.mySummary(windowDays),
  });
  const sessions = useQuery({
    queryKey: ["me-sessions"],
    queryFn: () => api.mySessions(undefined, 20),
  });

  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <Title className="font-ui">My activity</Title>
          <Text className="text-viberoi-sub">
            Your AI coding work over the last {windowDays} days.
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

      {summary.isLoading && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text>Loading…</Text>
        </Card>
      )}
      {summary.isError && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text className="text-red-400">
            {(summary.error as Error).message}
          </Text>
        </Card>
      )}

      {summary.data && (
        <>
          {/* Headline stats */}
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard label="Sessions" value={fmtInt(summary.data.sessions)} />
            <KpiCard
              label="My AI spend"
              value={fmtCurrency(summary.data.cost_usd)}
              hint="API-equivalent cost"
            />
            <KpiCard
              label="Tokens"
              value={fmtInt(summary.data.tokens)}
            />
            <KpiCard
              label="Avg session"
              value={fmtMinutes(summary.data.avg_session_duration_seconds)}
            />
          </div>

          {/* Code output */}
          <Card className="mt-6 bg-viberoi-card border-white/5">
            <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
              Code output
            </Text>
            <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3">
              <Mini
                label="Lines added"
                value={`+${fmtInt(summary.data.lines_added)}`}
                tone="emerald"
              />
              <Mini
                label="Lines deleted"
                value={`-${fmtInt(summary.data.lines_deleted)}`}
                tone="red"
              />
              <Mini
                label="Commits"
                value={fmtInt(summary.data.commit_count)}
              />
            </div>
          </Card>

          {/* Breakdowns */}
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs mb-2">
                My tool mix
              </Text>
              {summary.data.tool_mix.length === 0 ? (
                <Text className="text-viberoi-sub text-xs py-8 text-center">
                  No sessions yet
                </Text>
              ) : (
                <DonutChart
                  data={summary.data.tool_mix.map((t) => ({
                    name: t.tool_name,
                    value: parseFloat(t.cost_usd),
                  }))}
                  category="value"
                  index="name"
                  colors={["emerald", "blue", "violet", "amber", "rose"]}
                  valueFormatter={(n: number) => `$${n.toFixed(2)}`}
                  className="h-44"
                />
              )}
            </Card>

            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs mb-2">
                My mode mix
              </Text>
              {summary.data.mode_mix.length === 0 ? (
                <Text className="text-viberoi-sub text-xs py-8 text-center">
                  No mode data
                </Text>
              ) : (
                <DonutChart
                  data={summary.data.mode_mix.map((m) => ({
                    name: m.mode,
                    value: m.sessions,
                  }))}
                  category="value"
                  index="name"
                  colors={["emerald", "blue", "violet", "amber", "rose"]}
                  valueFormatter={(n: number) =>
                    `${n.toLocaleString()} sessions`
                  }
                  className="h-44"
                />
              )}
            </Card>

            <Card className="bg-viberoi-card border-white/5 p-0 overflow-hidden">
              <div className="px-4 pt-3 pb-1">
                <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                  My top tickets
                </Text>
              </div>
              {summary.data.top_tickets.length === 0 ? (
                <Text className="text-viberoi-sub text-xs py-8 text-center">
                  No tickets attributed yet
                </Text>
              ) : (
                <table className="w-full text-sm">
                  <tbody>
                    {summary.data.top_tickets.map((t) => (
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
              )}
            </Card>
          </div>

          {/* Model mix */}
          {summary.data.model_mix.length > 0 && (
            <Card className="mt-6 bg-viberoi-card border-white/5 p-0 overflow-hidden">
              <div className="px-6 pt-4 pb-2">
                <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                  My model usage
                </Text>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-viberoi-sub border-b border-white/5">
                    <th className="px-6 py-3 font-normal">Model</th>
                    <th className="px-6 py-3 font-normal text-right">Sessions</th>
                    <th className="px-6 py-3 font-normal text-right">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data.model_mix.map((m) => (
                    <tr
                      key={m.model}
                      className="border-b border-white/5 hover:bg-white/5"
                    >
                      <td className="px-6 py-3 font-mono text-xs">{m.model}</td>
                      <td className="px-6 py-3 text-right font-mono">
                        {m.sessions}
                      </td>
                      <td className="px-6 py-3 text-right font-mono">
                        ${parseFloat(m.cost_usd).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          {/* Recent sessions */}
          <Card className="mt-6 bg-viberoi-card border-white/5 p-0 overflow-hidden">
            <div className="px-6 pt-4 pb-2 flex items-center justify-between">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Recent sessions
              </Text>
              <button
                onClick={() => nav("/sessions")}
                className="text-xs text-viberoi-accent hover:underline"
              >
                View all →
              </button>
            </div>
            <RecentSessionsTable
              data={sessions.data?.items ?? []}
              isLoading={sessions.isLoading}
            />
          </Card>
        </>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card className="bg-viberoi-card border-white/5">
      <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
        {label}
      </Text>
      <Metric className="font-mono text-viberoi-text">{value}</Metric>
      {hint && (
        <Text className="text-[10px] text-viberoi-sub mt-1">{hint}</Text>
      )}
    </Card>
  );
}

function Mini({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "emerald" | "red";
}) {
  const colorMap: Record<string, string> = {
    emerald: "text-emerald-400",
    red: "text-red-400",
  };
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-viberoi-sub">
        {label}
      </div>
      <div
        className={`mt-0.5 font-mono ${tone ? colorMap[tone] : "text-viberoi-text"}`}
      >
        {value}
      </div>
    </div>
  );
}

function RecentSessionsTable({
  data,
  isLoading,
}: {
  data: SessionSummary[];
  isLoading: boolean;
}) {
  const nav = useNavigate();
  if (isLoading) {
    return <Text className="text-viberoi-sub py-8 text-center">Loading…</Text>;
  }
  if (data.length === 0) {
    return (
      <Text className="text-viberoi-sub py-8 text-center text-xs">
        No sessions yet — run the agent to capture your AI work.
      </Text>
    );
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wider text-viberoi-sub border-b border-white/5">
          <th className="px-6 py-3 font-normal">Started</th>
          <th className="px-6 py-3 font-normal">Tool</th>
          <th className="px-6 py-3 font-normal">Branch</th>
          <th className="px-6 py-3 font-normal text-right">Tokens</th>
          <th className="px-6 py-3 font-normal text-right">Cost</th>
        </tr>
      </thead>
      <tbody>
        {data.map((s) => (
          <tr
            key={s.id}
            className="border-b border-white/5 hover:bg-white/5 cursor-pointer"
            onClick={() => nav(`/sessions/${s.id}`)}
          >
            <td className="px-6 py-3 font-mono text-xs">
              {new Date(s.started_at).toLocaleString()}
            </td>
            <td className="px-6 py-3">{s.tool_name}</td>
            <td className="px-6 py-3 font-mono text-xs text-viberoi-sub">
              {s.branch_name ?? "—"}
            </td>
            <td className="px-6 py-3 text-right font-mono">
              {s.total_tokens.toLocaleString()}
            </td>
            <td className="px-6 py-3 text-right font-mono">
              ${parseFloat(s.cost_usd).toFixed(2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

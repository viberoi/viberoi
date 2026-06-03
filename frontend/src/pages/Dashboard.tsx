import { useQuery } from "@tanstack/react-query";
import { Card, Metric, Text, Title } from "@tremor/react";

import { api } from "../api/client";

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
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["kpis", 30],
    queryFn: () => api.kpiSnapshot(30),
  });

  return (
    <div>
      <Title className="font-ui">Dashboard</Title>
      <Text className="text-viberoi-sub">
        Rolling 30-day organization KPIs.
      </Text>

      {isLoading && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text>Loading…</Text>
        </Card>
      )}

      {isError && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text className="text-red-400">
            Failed to load KPIs: {(error as Error).message}
          </Text>
        </Card>
      )}

      {data && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard label="Total sessions" value={fmtInt(data.total_sessions)} />
          <KpiCard label="Total cost" value={fmtCurrency(data.total_cost_usd)} />
          <KpiCard
            label="Active developers"
            value={fmtInt(data.active_developers)}
          />
          <KpiCard
            label="Avg session"
            value={fmtMinutes(data.avg_session_duration_seconds)}
          />
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="bg-viberoi-card border-white/5">
      <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
        {label}
      </Text>
      <Metric className="font-mono text-viberoi-text">{value}</Metric>
    </Card>
  );
}

import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, Metric, Text, Title } from "@tremor/react";
import { ArrowLeft } from "lucide-react";

import { api } from "../api/client";

function fmtCurrency(s: string | number): string {
  const n = typeof s === "string" ? parseFloat(s) : s;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(n || 0);
}

export function SprintDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["sprint", id],
    queryFn: () => api.getSprint(id!),
    enabled: !!id,
  });

  return (
    <div>
      <Link
        to="/sprints"
        className="flex items-center gap-1 text-sm text-viberoi-sub hover:text-viberoi-text mb-4"
      >
        <ArrowLeft size={14} />
        Back to sprints
      </Link>

      {isLoading && (
        <Card className="bg-viberoi-card border-white/5">
          <Text>Loading…</Text>
        </Card>
      )}

      {isError && (
        <Card className="bg-viberoi-card border-white/5">
          <Text className="text-red-400">{(error as Error).message}</Text>
        </Card>
      )}

      {data && (
        <>
          <Title className="font-ui">{data.name}</Title>
          <Text className="text-viberoi-sub font-mono text-xs mt-1">
            {data.system}:{data.external_id} · {data.state}
          </Text>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
            <KpiCard label="Tickets" value={data.ticket_count.toString()} />
            <KpiCard
              label="Sessions"
              value={data.total_sessions.toString()}
            />
            <KpiCard
              label="Total cost"
              value={fmtCurrency(data.total_cost_usd)}
            />
            <KpiCard
              label="Days"
              value={
                data.started_at && data.ended_at
                  ? String(
                      Math.round(
                        (new Date(data.ended_at).getTime() -
                          new Date(data.started_at).getTime()) /
                          (1000 * 60 * 60 * 24),
                      ),
                    )
                  : "—"
              }
            />
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Window
              </Text>
              <div className="mt-2 text-sm">
                <Range
                  label="Started"
                  value={data.started_at}
                />
                <Range label="Ends" value={data.ended_at} />
                <Range label="Completed" value={data.completed_at} />
              </div>
            </Card>

            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Board
              </Text>
              <div className="mt-2 font-mono text-sm">
                {data.board_id ?? (
                  <span className="text-viberoi-sub">—</span>
                )}
              </div>
            </Card>
          </div>

          <Card className="mt-6 bg-viberoi-card border-white/5">
            <Text className="text-viberoi-sub">
              Per-ticket breakdown lands in batch 2 — currently the
              backend's per-sprint rollups are placeholders (the Worker's
              session-to-sprint join hasn't been wired in yet).
            </Text>
          </Card>
        </>
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

function Range({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div className="flex justify-between gap-4 py-1">
      <span className="text-viberoi-sub text-xs">{label}</span>
      <span className="font-mono text-xs">
        {value ? new Date(value).toLocaleString() : "—"}
      </span>
    </div>
  );
}

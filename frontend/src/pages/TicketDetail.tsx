import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";
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

export function TicketDetail() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => api.getTicket(id!),
    enabled: !!id,
  });

  return (
    <div>
      <button
        onClick={() => nav(-1)}
        className="flex items-center gap-1 text-sm text-viberoi-sub hover:text-viberoi-text mb-4"
      >
        <ArrowLeft size={14} />
        Back
      </button>

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
          <Title className="font-ui">{data.title}</Title>
          <Text className="text-viberoi-sub font-mono text-xs mt-1">
            {data.system}:{data.external_id} · {data.status}
            {data.priority ? ` · ${data.priority}` : ""}
          </Text>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Story points
              </Text>
              <div className="mt-1 font-mono">
                {data.story_points ?? "—"}
              </div>
            </Card>
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Sessions
              </Text>
              <div className="mt-1 font-mono">{data.total_sessions}</div>
            </Card>
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Cost
              </Text>
              <div className="mt-1 font-mono">
                {fmtCurrency(data.total_cost_usd)}
              </div>
            </Card>
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Created
              </Text>
              <div className="mt-1 font-mono text-sm">
                {new Date(data.created_at_external).toLocaleString()}
              </div>
            </Card>
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Closed
              </Text>
              <div className="mt-1 font-mono text-sm">
                {data.closed_at_external
                  ? new Date(data.closed_at_external).toLocaleString()
                  : "—"}
              </div>
            </Card>
          </div>

          {data.sprint_id && (
            <div className="mt-6">
              <Link
                to={`/sprints/${data.sprint_id}`}
                className="text-viberoi-accent hover:underline text-sm"
              >
                ← view sprint
              </Link>
            </div>
          )}

          <Card className="mt-6 bg-viberoi-card border-white/5">
            <Text className="text-viberoi-sub">
              Per-session list lands in batch 2 — currently the backend's
              per-ticket session count is a placeholder (the Worker join
              hasn't been wired in yet).
            </Text>
          </Card>
        </>
      )}
    </div>
  );
}

import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";
import { ArrowLeft } from "lucide-react";

import { api, type SessionSummary } from "../api/client";

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
  const sessions = useQuery({
    queryKey: ["ticket", id, "sessions"],
    queryFn: () => api.listSessionsForTicket(id!),
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

          <div className="mt-8">
            <Text className="font-ui text-sm uppercase tracking-wider text-viberoi-sub mb-2">
              Sessions attributed via branch parse
            </Text>
            <Card className="bg-viberoi-card border-white/5 p-0 overflow-hidden">
              <SessionsTable
                sessions={sessions.data?.items ?? []}
                isLoading={sessions.isLoading}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function SessionsTable({
  sessions,
  isLoading,
}: {
  sessions: SessionSummary[];
  isLoading: boolean;
}) {
  const nav = useNavigate();
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wider text-viberoi-sub border-b border-white/5">
          <th className="px-4 py-3 font-normal">Started</th>
          <th className="px-4 py-3 font-normal">Tool</th>
          <th className="px-4 py-3 font-normal">Branch</th>
          <th className="px-4 py-3 font-normal text-right">Tokens</th>
          <th className="px-4 py-3 font-normal text-right">Cost</th>
        </tr>
      </thead>
      <tbody>
        {isLoading && (
          <tr>
            <td colSpan={5} className="px-4 py-6 text-viberoi-sub">
              Loading…
            </td>
          </tr>
        )}
        {!isLoading && sessions.length === 0 && (
          <tr>
            <td colSpan={5} className="px-4 py-6 text-viberoi-sub">
              No sessions yet — the agent attributes via branch name.
              Sessions show up here once a branch matches this ticket's
              external id.
            </td>
          </tr>
        )}
        {sessions.map((s) => (
          <tr
            key={s.id}
            className="border-b border-white/5 hover:bg-white/5 cursor-pointer"
            onClick={() => nav(`/sessions/${s.id}`)}
          >
            <td className="px-4 py-3 font-mono text-xs">
              {new Date(s.started_at).toLocaleString()}
            </td>
            <td className="px-4 py-3">{s.tool_name}</td>
            <td className="px-4 py-3 font-mono text-xs text-viberoi-sub">
              {s.branch_name ?? "—"}
            </td>
            <td className="px-4 py-3 text-right font-mono">
              {s.total_tokens.toLocaleString()}
            </td>
            <td className="px-4 py-3 text-right font-mono">
              ${parseFloat(s.cost_usd).toFixed(2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

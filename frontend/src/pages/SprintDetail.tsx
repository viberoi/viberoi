import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, Metric, Text, Title } from "@tremor/react";
import { ArrowLeft } from "lucide-react";

import { api, type TicketDetail } from "../api/client";

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
  const tickets = useQuery({
    queryKey: ["sprint", id, "tickets"],
    queryFn: () => api.listTicketsInSprint(id!),
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

          <div className="mt-8">
            <Text className="font-ui text-sm uppercase tracking-wider text-viberoi-sub mb-2">
              Tickets in sprint
            </Text>
            <Card className="bg-viberoi-card border-white/5 p-0 overflow-hidden">
              <TicketsTable
                tickets={tickets.data?.items ?? []}
                isLoading={tickets.isLoading}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function TicketsTable({
  tickets,
  isLoading,
}: {
  tickets: TicketDetail[];
  isLoading: boolean;
}) {
  const nav = useNavigate();
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wider text-viberoi-sub border-b border-white/5">
          <th className="px-4 py-3 font-normal">External</th>
          <th className="px-4 py-3 font-normal">Title</th>
          <th className="px-4 py-3 font-normal">Status</th>
          <th className="px-4 py-3 font-normal">Priority</th>
          <th className="px-4 py-3 font-normal text-right">Story pts</th>
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
        {!isLoading && tickets.length === 0 && (
          <tr>
            <td colSpan={5} className="px-4 py-6 text-viberoi-sub">
              No tickets in this sprint yet.
            </td>
          </tr>
        )}
        {tickets.map((t) => (
          <tr
            key={t.id}
            className="border-b border-white/5 hover:bg-white/5 cursor-pointer"
            onClick={() => nav(`/tickets/${t.id}`)}
          >
            <td className="px-4 py-3 font-mono text-xs">{t.external_id}</td>
            <td className="px-4 py-3">{t.title}</td>
            <td className="px-4 py-3 text-viberoi-sub text-xs">
              {t.status}
            </td>
            <td className="px-4 py-3 text-viberoi-sub text-xs">
              {t.priority ?? "—"}
            </td>
            <td className="px-4 py-3 text-right font-mono">
              {t.story_points ?? "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
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

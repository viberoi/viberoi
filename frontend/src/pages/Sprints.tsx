import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";

import { api, type SprintSummary } from "../api/client";

const STATE_FILTERS = [
  { label: "Active", value: "active" },
  { label: "Future", value: "future" },
  { label: "Closed", value: "closed" },
] as const;

export function Sprints() {
  const [selected, setSelected] = useState<Set<string>>(new Set(["active"]));
  const states = Array.from(selected);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["sprints", states],
    queryFn: () => api.listSprints(states.length ? states : undefined),
  });

  function toggle(value: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }

  return (
    <div>
      <Title className="font-ui">Sprints</Title>
      <Text className="text-viberoi-sub">
        Connected to Jira / Linear / GitHub milestones via the Integration
        service.
      </Text>

      <div className="mt-4 flex items-center gap-2">
        {STATE_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => toggle(f.value)}
            className={[
              "px-3 py-1.5 rounded-md text-xs font-medium border",
              selected.has(f.value)
                ? "bg-viberoi-accent/10 border-viberoi-accent/30 text-viberoi-accent"
                : "border-white/10 text-viberoi-sub hover:text-viberoi-text",
            ].join(" ")}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isError && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text className="text-red-400">{(error as Error).message}</Text>
        </Card>
      )}

      <Card className="mt-6 bg-viberoi-card border-white/5 p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-viberoi-sub border-b border-white/5">
              <Th>Name</Th>
              <Th>System</Th>
              <Th>State</Th>
              <Th>Started</Th>
              <Th>Ends</Th>
              <Th className="text-right">Tickets</Th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <Empty colspan={6}>Loading…</Empty>
            )}
            {data?.items.length === 0 && (
              <Empty colspan={6}>
                No sprints found. Try another state filter, or connect a
                provider in Settings.
              </Empty>
            )}
            {data?.items.map((sp) => (
              <Row key={sp.id} sprint={sp} />
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function Th({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <th className={`px-4 py-3 font-normal ${className ?? ""}`}>{children}</th>
  );
}

function Empty({
  colspan,
  children,
}: {
  colspan: number;
  children: React.ReactNode;
}) {
  return (
    <tr>
      <td colSpan={colspan} className="px-4 py-6 text-viberoi-sub">
        {children}
      </td>
    </tr>
  );
}

function stateBadge(state: string) {
  const styles: Record<string, string> = {
    active: "bg-emerald-500/10 text-emerald-400",
    future: "bg-blue-500/10 text-blue-400",
    closed: "bg-viberoi-sub/20 text-viberoi-sub",
  };
  const cls = styles[state] ?? "bg-white/5 text-viberoi-text";
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider font-medium ${cls}`}>
      {state}
    </span>
  );
}

function Row({ sprint }: { sprint: SprintSummary }) {
  return (
    <tr className="border-b border-white/5 hover:bg-white/5">
      <td className="px-4 py-3">
        <Link
          to={`/sprints/${sprint.id}`}
          className="text-viberoi-text hover:text-viberoi-accent"
        >
          {sprint.name}
        </Link>
      </td>
      <td className="px-4 py-3 text-viberoi-sub uppercase text-xs tracking-wider">
        {sprint.system}
      </td>
      <td className="px-4 py-3">{stateBadge(sprint.state)}</td>
      <td className="px-4 py-3 text-viberoi-sub text-xs">
        {sprint.started_at
          ? new Date(sprint.started_at).toLocaleDateString()
          : "—"}
      </td>
      <td className="px-4 py-3 text-viberoi-sub text-xs">
        {sprint.ended_at
          ? new Date(sprint.ended_at).toLocaleDateString()
          : "—"}
      </td>
      <td className="px-4 py-3 text-right font-mono">
        {sprint.ticket_count}
      </td>
    </tr>
  );
}

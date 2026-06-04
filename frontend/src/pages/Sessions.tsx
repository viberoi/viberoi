import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";

import { api, type SessionSummary } from "../api/client";

const PAGE_SIZE = 25;

export function Sessions() {
  // Stack of cursors used to support "Back" without server-side history.
  const [cursorStack, setCursorStack] = useState<(string | null)[]>([null]);
  const cursor = cursorStack[cursorStack.length - 1];

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["sessions", cursor, PAGE_SIZE],
    queryFn: () => api.listSessions(cursor ?? undefined, PAGE_SIZE),
    placeholderData: keepPreviousData,
  });

  const hasNext = !!data?.next_cursor;
  const hasPrev = cursorStack.length > 1;

  return (
    <div>
      <Title className="font-ui">Sessions</Title>
      <Text className="text-viberoi-sub">
        Recent AI-coding sessions captured by the agent.
      </Text>

      {isError && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text className="text-red-400">
            Failed to load sessions: {(error as Error).message}
          </Text>
        </Card>
      )}

      <Card className="mt-6 bg-viberoi-card border-white/5 p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-viberoi-sub border-b border-white/5">
              <Th>Started</Th>
              <Th>Tool</Th>
              <Th>Model</Th>
              <Th>Branch</Th>
              <Th className="text-right">Tokens</Th>
              <Th className="text-right">Cost</Th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-viberoi-sub">
                  Loading…
                </td>
              </tr>
            )}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-viberoi-sub">
                  No sessions in range. Have you connected the agent yet?
                </td>
              </tr>
            )}
            {data?.items.map((s) => (
              <Row key={s.id} session={s} />
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mt-4 flex items-center justify-between">
        <button
          disabled={!hasPrev}
          onClick={() => setCursorStack((s) => s.slice(0, -1))}
          className="px-3 py-1.5 rounded-md text-sm border border-white/10 disabled:opacity-30 hover:bg-white/5"
        >
          ← Previous
        </button>
        <div className="text-xs text-viberoi-sub">
          {data?.items.length ?? 0} rows
        </div>
        <button
          disabled={!hasNext}
          onClick={() =>
            data?.next_cursor &&
            setCursorStack((s) => [...s, data.next_cursor!])
          }
          className="px-3 py-1.5 rounded-md text-sm border border-white/10 disabled:opacity-30 hover:bg-white/5"
        >
          Next →
        </button>
      </div>
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

function Row({ session }: { session: SessionSummary }) {
  const nav = useNavigate();
  return (
    <tr
      className="border-b border-white/5 hover:bg-white/5 cursor-pointer"
      onClick={() => nav(`/sessions/${session.id}`)}
    >
      <td className="px-4 py-3 font-mono text-xs">
        {new Date(session.started_at).toLocaleString()}
      </td>
      <td className="px-4 py-3">{session.tool_name}</td>
      <td className="px-4 py-3 text-viberoi-sub">{session.model}</td>
      <td className="px-4 py-3 font-mono text-xs text-viberoi-sub">
        {session.branch_name ?? "—"}
      </td>
      <td className="px-4 py-3 text-right font-mono">
        {session.total_tokens.toLocaleString()}
      </td>
      <td className="px-4 py-3 text-right font-mono">
        ${parseFloat(session.cost_usd).toFixed(2)}
      </td>
    </tr>
  );
}

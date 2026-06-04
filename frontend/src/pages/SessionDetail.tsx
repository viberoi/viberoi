import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";
import { ArrowLeft } from "lucide-react";

import { api } from "../api/client";

function fmtDuration(seconds: number | null): string {
  if (seconds === null || seconds <= 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function fmtCurrency(s: string | number): string {
  const n = typeof s === "string" ? parseFloat(s) : s;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(n || 0);
}

export function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["session", id],
    queryFn: () => api.getSession(id!),
    enabled: !!id,
  });

  return (
    <div>
      <Link
        to="/sessions"
        className="flex items-center gap-1 text-sm text-viberoi-sub hover:text-viberoi-text mb-4"
      >
        <ArrowLeft size={14} />
        Back to sessions
      </Link>

      <Title className="font-ui">Session detail</Title>

      {isLoading && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text>Loading…</Text>
        </Card>
      )}

      {isError && (
        <Card className="mt-6 bg-viberoi-card border-white/5">
          <Text className="text-red-400">
            {(error as Error).message}
          </Text>
        </Card>
      )}

      {data && (
        <>
          <Text className="font-mono text-viberoi-sub text-xs mt-1">
            {data.external_id}
          </Text>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Field label="Tool" value={data.tool_name} />
            <Field label="Model" value={data.model} mono />
            <Field label="Branch" value={data.branch_name ?? "—"} mono />
            <Field
              label="Started"
              value={new Date(data.started_at).toLocaleString()}
            />
            <Field
              label="Duration"
              value={fmtDuration(data.duration_seconds)}
            />
            <Field
              label="Total tokens"
              value={data.total_tokens.toLocaleString()}
              mono
            />
            <Field
              label="Cost"
              value={fmtCurrency(data.cost_usd)}
              mono
            />
            <Field
              label="Files touched"
              value={String(data.files_touched_count)}
              mono
            />
            <Field
              label="Schema"
              value={`v${data.schema_version}`}
              mono
            />
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Ticket
              </Text>
              <div className="mt-2 font-mono">
                {data.ticket_external_id ?? (
                  <span className="text-viberoi-sub">Unattributed</span>
                )}
              </div>
            </Card>

            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Attribution signals
              </Text>
              <div className="mt-2 flex flex-wrap gap-1">
                {data.attribution_signals.length === 0 ? (
                  <span className="text-viberoi-sub text-sm">No signals</span>
                ) : (
                  data.attribution_signals.map((s) => (
                    <span
                      key={s}
                      className="text-xs font-mono bg-viberoi-accent/10 text-viberoi-accent px-2 py-1 rounded"
                    >
                      {s}
                    </span>
                  ))
                )}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <Card className="bg-viberoi-card border-white/5">
      <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
        {label}
      </Text>
      <div className={`mt-1 ${mono ? "font-mono" : ""}`}>{value}</div>
    </Card>
  );
}

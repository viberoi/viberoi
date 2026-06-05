import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";
import { ArrowLeft, GitCommit, Info } from "lucide-react";

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

function fmtInt(n: number): string {
  return n.toLocaleString();
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
          <Text className="text-red-400">{(error as Error).message}</Text>
        </Card>
      )}

      {data && (
        <>
          <div className="flex items-center gap-2 mt-1">
            <Text className="font-mono text-viberoi-sub text-xs">
              {data.external_id}
            </Text>
            <Badge label={data.tool_name} />
            {data.is_agentic && <Badge label="agentic" tone="accent" />}
            {data.is_committed && (
              <Badge label="committed" tone="emerald" icon={<GitCommit size={10} />} />
            )}
            {data.is_estimated && (
              <Badge
                label="estimated cost"
                tone="amber"
                tooltip="Cost is the equivalent-API figure. The user is on a subscription plan or the model rate is approximate."
              />
            )}
          </div>

          {/* Headline stats */}
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Total tokens" value={fmtInt(data.total_tokens)} />
            <Stat label="Cost" value={fmtCurrency(data.cost_usd)} />
            <Stat
              label="Duration"
              value={fmtDuration(data.duration_seconds)}
            />
            <Stat label="Turns" value={fmtInt(data.turn_count)} />
          </div>

          {/* Token breakdown */}
          <Card className="mt-6 bg-viberoi-card border-white/5">
            <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
              Token breakdown
            </Text>
            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
              <Mini label="Input" value={fmtInt(data.tokens_input)} />
              <Mini label="Output" value={fmtInt(data.tokens_output)} />
              <Mini label="Cache read" value={fmtInt(data.tokens_cache_read)} />
              <Mini label="Cache write" value={fmtInt(data.tokens_cache_write)} />
            </div>
          </Card>

          {/* Code output + activity */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Code output
              </Text>
              <div className="mt-3 grid grid-cols-3 gap-3">
                <Mini
                  label="Added"
                  value={`+${fmtInt(data.lines_added)}`}
                  tone="emerald"
                />
                <Mini
                  label="Deleted"
                  value={`-${fmtInt(data.lines_deleted)}`}
                  tone="red"
                />
                <Mini label="Commits" value={fmtInt(data.commit_count)} />
              </div>
            </Card>
            <Card className="bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Activity
              </Text>
              <div className="mt-3 grid grid-cols-3 gap-3">
                <Mini label="Mode" value={data.mode} />
                <Mini label="Subagents" value={fmtInt(data.subagent_count)} />
                <Mini
                  label="Files"
                  value={fmtInt(data.files_touched_count)}
                />
              </div>
            </Card>
          </div>

          {/* Attribution */}
          <Card className="mt-6 bg-viberoi-card border-white/5">
            <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
              Attribution
            </Text>
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field
                label="Ticket"
                value={
                  data.ticket_external_id ?? (
                    <span className="text-viberoi-sub italic">
                      Unattributed
                    </span>
                  )
                }
              />
              <Field
                label="Method"
                value={data.attribution_method ?? "—"}
                mono
              />
              <Field
                label="Confidence"
                value={
                  data.attribution_confidence !== null
                    ? `${(data.attribution_confidence * 100).toFixed(0)}%`
                    : "—"
                }
                mono
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-1">
              {data.attribution_signals.length === 0 ? (
                <span className="text-viberoi-sub text-xs">No signals</span>
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

          {/* Quality (if present) */}
          {(data.session_restarts !== null ||
            data.file_oscillations !== null) && (
            <Card className="mt-6 bg-viberoi-card border-white/5">
              <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                Quality signals
              </Text>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <Mini
                  label="Session restarts"
                  value={
                    data.session_restarts !== null
                      ? String(data.session_restarts)
                      : "—"
                  }
                />
                <Mini
                  label="File oscillations"
                  value={
                    data.file_oscillations !== null
                      ? String(data.file_oscillations)
                      : "—"
                  }
                />
              </div>
            </Card>
          )}

          {/* Repo */}
          <Card className="mt-6 bg-viberoi-card border-white/5">
            <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
              Repository
            </Text>
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field
                label="Name"
                value={data.repo_name ?? "—"}
                mono
              />
              <Field
                label="Branch"
                value={data.branch_name ?? "—"}
                mono
              />
              <Field
                label="Model"
                value={data.model}
                mono
              />
            </div>
            {data.repo_cwd && (
              <div className="mt-3 text-xs font-mono text-viberoi-sub truncate">
                {data.repo_cwd}
              </div>
            )}
          </Card>

          {/* Files touched */}
          {data.files_touched.length > 0 && (
            <Card className="mt-6 bg-viberoi-card border-white/5">
              <div className="flex items-center justify-between mb-3">
                <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
                  Files touched ({data.files_touched_count})
                </Text>
                <Text className="text-[10px] text-viberoi-sub">
                  paths only — never file contents
                </Text>
              </div>
              <div className="font-mono text-xs space-y-1 max-h-64 overflow-y-auto">
                {data.files_touched.map((f) => (
                  <div
                    key={f}
                    className="text-viberoi-sub truncate hover:text-viberoi-text"
                    title={f}
                  >
                    {f}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card className="bg-viberoi-card border-white/5">
      <Text className="text-viberoi-sub uppercase tracking-wider text-xs">
        {label}
      </Text>
      <div className="mt-1 font-mono text-2xl">{value}</div>
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

function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-viberoi-sub">
        {label}
      </div>
      <div className={`mt-0.5 ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}

function Badge({
  label,
  tone = "default",
  icon,
  tooltip,
}: {
  label: string;
  tone?: "default" | "accent" | "emerald" | "amber";
  icon?: React.ReactNode;
  tooltip?: string;
}) {
  const tones: Record<string, string> = {
    default: "bg-white/5 text-viberoi-sub",
    accent: "bg-viberoi-accent/15 text-viberoi-accent",
    emerald: "bg-emerald-500/15 text-emerald-300",
    amber: "bg-amber-500/15 text-amber-300",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded ${tones[tone]}`}
      title={tooltip}
    >
      {icon}
      {label}
      {tooltip && <Info size={9} className="opacity-50" />}
    </span>
  );
}

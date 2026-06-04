import { useQuery } from "@tanstack/react-query";
import { Card, Text } from "@tremor/react";

import { api } from "../../api/client";

export function Profile() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.me(),
  });

  if (isLoading) {
    return (
      <Card className="bg-viberoi-card border-white/5">
        <Text>Loading…</Text>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card className="bg-viberoi-card border-white/5">
        <Text className="text-red-400">{(error as Error).message}</Text>
      </Card>
    );
  }

  if (!data) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
      <Field label="Email" value={data.email} />
      <Field label="Role" value={data.role} />
      <Field
        label="GitHub username"
        value={data.github_username ?? "—"}
        mono
      />
      <Field label="Team" value={data.team_id ?? "—"} mono />
      <Field label="Agent status" value={data.agent_status} />
      <Field
        label="Joined"
        value={new Date(data.created_at).toLocaleDateString()}
      />
      <Field
        label="Last active"
        value={
          data.last_active_at
            ? new Date(data.last_active_at).toLocaleString()
            : "—"
        }
      />
      <Field label="Org id" value={data.org_id} mono />
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
      <div className={`mt-1 ${mono ? "font-mono text-sm" : ""} break-all`}>
        {value}
      </div>
    </Card>
  );
}

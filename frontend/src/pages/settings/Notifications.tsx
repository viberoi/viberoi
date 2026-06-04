import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";
import { Slack } from "lucide-react";

import { api, type NotificationChannelSummary } from "../../api/client";

export function Notifications() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["channels"],
    queryFn: () => api.listChannels(),
  });

  const slack = data?.items.find((c) => c.channel === "slack");

  return (
    <div className="space-y-4">
      <Card className="bg-viberoi-card border-white/5">
        <Title className="font-ui text-base">Notification channels</Title>
        <Text className="text-viberoi-sub text-sm">
          Slack-only for V1. Teams and email land in a follow-up.
        </Text>
      </Card>

      {isError && (
        <Card className="bg-red-500/10 border-red-500/30">
          <Text className="text-red-300">{(error as Error).message}</Text>
        </Card>
      )}

      {isLoading ? (
        <Card className="bg-viberoi-card border-white/5">
          <Text>Loading…</Text>
        </Card>
      ) : (
        <SlackPanel current={slack} onMutated={() => qc.invalidateQueries({ queryKey: ["channels"] })} />
      )}
    </div>
  );
}

function SlackPanel({
  current,
  onMutated,
}: {
  current: NotificationChannelSummary | undefined;
  onMutated: () => void;
}) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const upsert = useMutation({
    mutationFn: (webhookUrl: string) => api.upsertChannel("slack", webhookUrl),
    onSuccess: () => {
      setUrl("");
      setError(null);
      onMutated();
    },
    onError: (err: Error) => setError(err.message),
  });

  const disable = useMutation({
    mutationFn: () => api.disableChannel("slack"),
    onSuccess: onMutated,
  });

  const configured = current && current.has_webhook_url && current.enabled;

  return (
    <Card className="bg-viberoi-card border-white/5">
      <div className="flex items-center gap-2 mb-3">
        <Slack size={16} className="text-viberoi-accent" />
        <span className="font-ui font-semibold">Slack</span>
        <span className="ml-auto text-[10px] uppercase tracking-wider">
          {configured ? (
            <span className="text-emerald-400">Configured</span>
          ) : current && !current.enabled ? (
            <span className="text-amber-400">Disabled</span>
          ) : (
            <span className="text-viberoi-sub">Not set</span>
          )}
        </span>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!url.startsWith("https://hooks.slack.com/")) {
            setError("Use the incoming-webhook URL from Slack (https://hooks.slack.com/…).");
            return;
          }
          upsert.mutate(url);
        }}
        className="space-y-2"
      >
        <label className="block text-xs uppercase tracking-wider text-viberoi-sub">
          Webhook URL
        </label>
        <input
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={
            configured
              ? "Set — enter a new URL to replace"
              : "https://hooks.slack.com/services/T.../B.../..."
          }
          className="w-full px-3 py-2 rounded-md bg-viberoi-bg border border-white/10 text-sm font-mono focus:outline-none focus:border-viberoi-accent"
        />
        {error && (
          <div className="text-xs text-red-400">{error}</div>
        )}
        <div className="flex items-center gap-2 pt-1">
          <button
            type="submit"
            disabled={!url || upsert.isPending}
            className="px-3 py-1.5 rounded-md text-xs bg-viberoi-accent/10 border border-viberoi-accent/30 text-viberoi-accent hover:bg-viberoi-accent/20 disabled:opacity-50"
          >
            {upsert.isPending ? "Saving…" : configured ? "Update" : "Save"}
          </button>
          {configured && (
            <button
              type="button"
              onClick={() => {
                if (
                  confirm(
                    "Disable Slack notifications? You can re-enable by saving a new webhook URL.",
                  )
                ) {
                  disable.mutate();
                }
              }}
              disabled={disable.isPending}
              className="px-3 py-1.5 rounded-md text-xs border border-white/10 hover:bg-white/5 disabled:opacity-50"
            >
              Disable
            </button>
          )}
        </div>
      </form>

      <div className="mt-4 text-xs text-viberoi-sub">
        The webhook URL is KMS-encrypted at rest. The backend SSRF guard
        rejects anything that doesn't resolve to a public Slack IP.
      </div>
    </Card>
  );
}

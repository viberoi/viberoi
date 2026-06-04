import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";
import { CheckCircle2, Github, Plug, RefreshCw, X } from "lucide-react";

import { api, type IntegrationSummary } from "../../api/client";

const PROVIDERS = [
  { id: "github", label: "GitHub", Icon: Github },
  { id: "jira", label: "Jira", Icon: Plug },
  { id: "linear", label: "Linear", Icon: Plug },
] as const;

export function Integrations() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [banner, setBanner] = useState<
    { kind: "ok" | "err"; msg: string } | null
  >(null);

  // OAuth callback redirects here with ?status=ok&id=... or ?err=<code>.
  useEffect(() => {
    const status = searchParams.get("status");
    const err = searchParams.get("err");
    if (status === "ok") {
      setBanner({ kind: "ok", msg: "Integration connected." });
      setSearchParams({}, { replace: true });
      qc.invalidateQueries({ queryKey: ["integrations"] });
    } else if (err) {
      setBanner({
        kind: "err",
        msg:
          err === "user_cancelled"
            ? "Connection cancelled."
            : err === "oauth_state"
            ? "OAuth state mismatch — try connecting again."
            : `Connection failed (${err}).`,
      });
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams, qc]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => api.listIntegrations(),
  });

  const connect = useMutation({
    mutationFn: (provider: string) => api.connectIntegration(provider),
    onSuccess: (resp) => {
      // Hand off to the provider's OAuth page; on return, the callback
      // redirects back to /settings/integrations.
      window.location.href = resp.authorize_url;
    },
    onError: (err: Error) =>
      setBanner({ kind: "err", msg: err.message }),
  });

  const disconnect = useMutation({
    mutationFn: (provider: string) => api.disconnectIntegration(provider),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations"] }),
    onError: (err: Error) =>
      setBanner({ kind: "err", msg: err.message }),
  });

  const sync = useMutation({
    mutationFn: (provider: string) => api.syncIntegration(provider),
    onSuccess: () =>
      setBanner({ kind: "ok", msg: "Sync enqueued." }),
    onError: (err: Error) =>
      setBanner({ kind: "err", msg: err.message }),
  });

  const byProvider = new Map<string, IntegrationSummary>();
  data?.forEach((i) => byProvider.set(i.provider, i));

  return (
    <div className="space-y-4">
      <Card className="bg-viberoi-card border-white/5">
        <Title className="font-ui text-base">Integrations</Title>
        <Text className="text-viberoi-sub text-sm">
          Connect ticket + PR sources so the agent can attribute work.
          OrgAdmin only.
        </Text>
      </Card>

      {banner && (
        <Card
          className={
            banner.kind === "ok"
              ? "bg-emerald-500/10 border-emerald-500/30"
              : "bg-red-500/10 border-red-500/30"
          }
        >
          <div className="flex items-center gap-2 text-sm">
            {banner.kind === "ok" ? (
              <CheckCircle2 size={14} className="text-emerald-400" />
            ) : (
              <X size={14} className="text-red-400" />
            )}
            <span>{banner.msg}</span>
            <button
              onClick={() => setBanner(null)}
              className="ml-auto text-viberoi-sub hover:text-viberoi-text"
            >
              <X size={12} />
            </button>
          </div>
        </Card>
      )}

      {isError && (
        <Card className="bg-red-500/10 border-red-500/30">
          <Text className="text-red-300">{(error as Error).message}</Text>
        </Card>
      )}

      <div className="space-y-3">
        {isLoading
          ? PROVIDERS.map((p) => (
              <Card key={p.id} className="bg-viberoi-card border-white/5">
                <Text className="text-viberoi-sub">Loading {p.label}…</Text>
              </Card>
            ))
          : PROVIDERS.map((p) => (
              <ProviderRow
                key={p.id}
                provider={p}
                integration={byProvider.get(p.id)}
                onConnect={() => connect.mutate(p.id)}
                onDisconnect={() => {
                  if (
                    confirm(
                      `Disconnect ${p.label}? Webhooks will stop, and re-connecting requires going through OAuth again.`,
                    )
                  ) {
                    disconnect.mutate(p.id);
                  }
                }}
                onSync={() => sync.mutate(p.id)}
                isConnecting={connect.isPending}
                isSyncing={sync.isPending && sync.variables === p.id}
              />
            ))}
      </div>
    </div>
  );
}

function ProviderRow({
  provider,
  integration,
  onConnect,
  onDisconnect,
  onSync,
  isConnecting,
  isSyncing,
}: {
  provider: (typeof PROVIDERS)[number];
  integration: IntegrationSummary | undefined;
  onConnect: () => void;
  onDisconnect: () => void;
  onSync: () => void;
  isConnecting: boolean;
  isSyncing: boolean;
}) {
  const connected = integration && !integration.revoked;
  const webhookOk =
    integration?.webhook_registration_status === "ok";

  return (
    <Card className="bg-viberoi-card border-white/5">
      <div className="flex items-center gap-3">
        <provider.Icon size={20} className="text-viberoi-accent" />
        <div className="flex-1">
          <div className="font-ui font-semibold">{provider.label}</div>
          <div className="text-xs text-viberoi-sub">
            {connected ? (
              <>
                <span className="text-emerald-400">Connected</span>
                {webhookOk ? " · webhook registered" : " · webhook pending"}
                {integration!.last_sync_at && (
                  <> · last sync {new Date(integration!.last_sync_at).toLocaleString()}</>
                )}
              </>
            ) : (
              "Not connected"
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <>
              <button
                onClick={onSync}
                disabled={isSyncing}
                className="px-3 py-1.5 rounded-md text-xs border border-white/10 hover:bg-white/5 flex items-center gap-1 disabled:opacity-50"
              >
                <RefreshCw size={12} />
                Sync
              </button>
              <button
                onClick={onDisconnect}
                className="px-3 py-1.5 rounded-md text-xs border border-red-500/30 text-red-300 hover:bg-red-500/10"
              >
                Disconnect
              </button>
            </>
          ) : (
            <button
              onClick={onConnect}
              disabled={isConnecting}
              className="px-3 py-1.5 rounded-md text-xs bg-viberoi-accent/10 border border-viberoi-accent/30 text-viberoi-accent hover:bg-viberoi-accent/20 disabled:opacity-50"
            >
              {isConnecting ? "Redirecting…" : "Connect"}
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}

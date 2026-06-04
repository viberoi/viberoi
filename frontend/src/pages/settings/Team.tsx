import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Card, Text, Title } from "@tremor/react";
import { CheckCircle2, Mail, X } from "lucide-react";

import { ApiError, api, type InviteResponse } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";

export function Team() {
  const { user } = useAuth();
  const [email, setEmail] = useState("");
  const [banner, setBanner] = useState<
    { kind: "ok"; resp: InviteResponse } | { kind: "err"; msg: string } | null
  >(null);

  const isOrgAdmin = user?.role === "OrgAdmin";

  const invite = useMutation({
    mutationFn: (e: string) => api.inviteTeammate(e),
    onSuccess: (resp) => {
      setBanner({ kind: "ok", resp });
      setEmail("");
    },
    onError: (err: Error) => {
      const msg =
        err instanceof ApiError
          ? `${err.status}: ${err.message}`
          : err.message;
      setBanner({ kind: "err", msg });
    },
  });

  if (!isOrgAdmin) {
    return (
      <Card className="bg-viberoi-card border-white/5">
        <Title className="font-ui text-base">Team</Title>
        <Text className="text-viberoi-sub text-sm mt-2">
          Only OrgAdmins can invite teammates. Ask your org admin to invite
          you.
        </Text>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="bg-viberoi-card border-white/5">
        <Title className="font-ui text-base">Invite a teammate</Title>
        <Text className="text-viberoi-sub text-sm">
          Cognito sends them an email with a temporary password. They sign
          in via the Hosted UI, set a real password, and land in your org
          as a Developer.
        </Text>
        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!email.trim()) return;
            invite.mutate(email.trim().toLowerCase());
          }}
        >
          <div className="flex-1 flex items-center gap-2 bg-viberoi-surface border border-white/5 rounded-md px-3">
            <Mail size={14} className="text-viberoi-sub" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alice@yourcompany.com"
              required
              disabled={invite.isPending}
              className="flex-1 bg-transparent py-2 outline-none text-sm placeholder:text-viberoi-sub disabled:opacity-50"
            />
          </div>
          <button
            type="submit"
            disabled={invite.isPending || !email.trim()}
            className="px-4 py-2 rounded-md bg-viberoi-accent text-black text-sm font-semibold hover:bg-viberoi-accent/90 disabled:opacity-50"
          >
            {invite.isPending ? "Sending…" : "Send invite"}
          </button>
        </form>
        <Text className="text-viberoi-sub text-xs mt-2">
          Email domain must match your org domain (one org per domain rule).
        </Text>
      </Card>

      {banner?.kind === "ok" && (
        <Card className="bg-emerald-500/10 border-emerald-500/30">
          <div className="flex items-start gap-2 text-sm">
            <CheckCircle2 size={14} className="text-emerald-400 mt-0.5" />
            <div className="flex-1">
              <div className="font-semibold">
                Invited {banner.resp.email}
              </div>
              <div className="text-viberoi-sub text-xs mt-1">
                {banner.resp.message}
              </div>
            </div>
            <button
              onClick={() => setBanner(null)}
              className="text-viberoi-sub hover:text-viberoi-text"
            >
              <X size={12} />
            </button>
          </div>
        </Card>
      )}

      {banner?.kind === "err" && (
        <Card className="bg-red-500/10 border-red-500/30">
          <div className="flex items-start gap-2 text-sm">
            <X size={14} className="text-red-400 mt-0.5" />
            <div className="flex-1 font-mono text-xs">{banner.msg}</div>
            <button
              onClick={() => setBanner(null)}
              className="text-viberoi-sub hover:text-viberoi-text"
            >
              <X size={12} />
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}

import { Card, Text, Title } from "@tremor/react";

export function IntegrationsPlaceholder() {
  return (
    <Card className="bg-viberoi-card border-white/5">
      <Title className="font-ui text-base">Integrations</Title>
      <Text className="text-viberoi-sub mt-2">
        Connect GitHub / Jira / Linear to pull tickets + sprints. Write
        flows land in batch 2 — for now you can list connected providers
        and start OAuth via the backend's <code>POST
        /integrations/&#123;provider&#125;/connect</code> route.
      </Text>
    </Card>
  );
}

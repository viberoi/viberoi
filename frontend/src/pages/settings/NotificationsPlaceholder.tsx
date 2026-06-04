import { Card, Text, Title } from "@tremor/react";

export function NotificationsPlaceholder() {
  return (
    <Card className="bg-viberoi-card border-white/5">
      <Title className="font-ui text-base">Notifications</Title>
      <Text className="text-viberoi-sub mt-2">
        Slack delivery is wired end-to-end (Notification service drains
        the SQS queue). The channel-config UI lands in batch 2 along with
        a small backend addition for the upsert HTTP route.
      </Text>
    </Card>
  );
}

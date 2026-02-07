"use client";

import type { InboxMessage } from "@/types";
import { MessageCard } from "./message-card";

interface MessageListProps {
  messages: InboxMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-dashed">
        <div className="text-center">
          <p className="text-lg font-medium text-muted-foreground">
            Žádné zprávy
          </p>
          <p className="text-sm text-muted-foreground">
            V této kategorii nejsou žádné zprávy
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {messages.map((message) => (
        <MessageCard key={message.id} message={message} />
      ))}
    </div>
  );
}

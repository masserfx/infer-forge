"use client";

import { MessageList } from "@/components/inbox/message-list";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getInboxMessages } from "@/lib/api";
import type { InboxStatus } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { Inbox } from "lucide-react";
import { useState } from "react";

type TabValue = "all" | InboxStatus;

export default function InboxPage() {
  const [activeTab, setActiveTab] = useState<TabValue>("all");

  const { data: messages, isLoading } = useQuery({
    queryKey: ["inbox", { status: activeTab }],
    queryFn: () =>
      getInboxMessages({
        status: activeTab !== "all" ? activeTab : undefined,
      }),
  });

  const tabCounts = {
    all: messages?.length || 0,
    new: messages?.filter((m) => m.status === "new").length || 0,
    classified: messages?.filter((m) => m.status === "classified").length || 0,
    assigned: messages?.filter((m) => m.status === "assigned").length || 0,
  };

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <div className="flex items-center gap-3">
        <Inbox className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Příchozí pošta</h1>
          <p className="text-muted-foreground">
            AI klasifikace a přiřazení e-mailů
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabValue)}>
        <TabsList>
          <TabsTrigger value="all">
            Vše
            {tabCounts.all > 0 && (
              <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs">
                {tabCounts.all}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="new">
            Nové
            {tabCounts.new > 0 && (
              <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800">
                {tabCounts.new}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="classified">
            Klasifikované
            {tabCounts.classified > 0 && (
              <span className="ml-2 rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800">
                {tabCounts.classified}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="assigned">
            Přiřazené
            {tabCounts.assigned > 0 && (
              <span className="ml-2 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">
                {tabCounts.assigned}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        {isLoading ? (
          <div className="flex min-h-[400px] items-center justify-center rounded-lg border">
            <div className="text-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="mt-4 text-sm text-muted-foreground">
                Načítání zpráv...
              </p>
            </div>
          </div>
        ) : (
          <>
            <TabsContent value="all">
              <MessageList messages={messages || []} />
            </TabsContent>
            <TabsContent value="new">
              <MessageList
                messages={messages?.filter((m) => m.status === "new") || []}
              />
            </TabsContent>
            <TabsContent value="classified">
              <MessageList
                messages={
                  messages?.filter((m) => m.status === "classified") || []
                }
              />
            </TabsContent>
            <TabsContent value="assigned">
              <MessageList
                messages={messages?.filter((m) => m.status === "assigned") || []}
              />
            </TabsContent>
          </>
        )}
      </Tabs>
    </div>
  );
}

"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ClipboardList,
  Factory,
  Inbox,
  FileText,
} from "lucide-react";

interface StatsCardsProps {
  totalOrders: number;
  inProduction: number;
  newMessages: number;
  pendingInvoices: number;
}

export function StatsCards({
  totalOrders,
  inProduction,
  newMessages,
  pendingInvoices,
}: StatsCardsProps) {
  const stats = [
    {
      title: "Celkem zakázek",
      value: totalOrders,
      icon: ClipboardList,
      description: "Aktivní zakázky",
    },
    {
      title: "Ve výrobě",
      value: inProduction,
      icon: Factory,
      description: "Právě se vyrábí",
    },
    {
      title: "Nové zprávy",
      value: newMessages,
      icon: Inbox,
      description: "Neklasifikované",
    },
    {
      title: "Čeká na fakturaci",
      value: pendingInvoices,
      icon: FileText,
      description: "K vystavení faktury",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-xs sm:text-sm font-medium">
                {stat.title}
              </CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <div className="text-xl sm:text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

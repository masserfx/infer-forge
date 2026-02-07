"use client";

import { useQuery } from "@tanstack/react-query";
import { getOrders, getInboxMessages } from "@/lib/api";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { PipelineChart } from "@/components/dashboard/pipeline-chart";
import { RecentOrders } from "@/components/dashboard/recent-orders";
import type { OrderStatus } from "@/types";

export default function DashboardPage() {
  // Fetch all orders
  const { data: orders = [], isLoading: ordersLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: () => getOrders(),
  });

  // Fetch inbox messages
  const { data: inboxMessages = [], isLoading: inboxLoading } = useQuery({
    queryKey: ["inbox", "new"],
    queryFn: () => getInboxMessages({ status: "new" }),
  });

  // Calculate statistics
  const totalOrders = orders.length;
  const inProduction = orders.filter((o) => o.status === "vyroba").length;
  const newMessages = inboxMessages.length;
  const pendingInvoices = orders.filter((o) => o.status === "fakturace").length;

  // Calculate status counts for pipeline
  const statusCounts = orders.reduce(
    (acc, order) => {
      acc[order.status] = (acc[order.status] || 0) + 1;
      return acc;
    },
    {} as Record<OrderStatus, number>
  );

  // Get recent orders (last 10, sorted by creation date)
  const recentOrders = [...orders]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 10);

  if (ordersLoading || inboxLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-muted-foreground">Načítání...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Přehled aktivních zakázek a zpráv
        </p>
      </div>

      <StatsCards
        totalOrders={totalOrders}
        inProduction={inProduction}
        newMessages={newMessages}
        pendingInvoices={pendingInvoices}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <PipelineChart statusCounts={statusCounts} />
        <div className="lg:col-span-2">
          <RecentOrders orders={recentOrders} />
        </div>
      </div>
    </div>
  );
}

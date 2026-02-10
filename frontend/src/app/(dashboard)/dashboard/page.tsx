"use client";

import { useQuery } from "@tanstack/react-query";
import { getDashboardStats, getOrders } from "@/lib/api";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { PipelineChart } from "@/components/dashboard/pipeline-chart";
import { RecentOrders } from "@/components/dashboard/recent-orders";
import { Recommendations } from "@/components/dashboard/recommendations";
import type { OrderStatus } from "@/types";

export default function DashboardPage() {
  // Fetch aggregated stats from the API (instead of fetching ALL orders)
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => getDashboardStats(),
  });

  // Fetch only the 10 most recent orders for the list
  const { data: recentOrders = [], isLoading: ordersLoading } = useQuery({
    queryKey: ["orders", "recent"],
    queryFn: () => getOrders({ limit: 10 }),
  });

  // Convert pipeline statuses array to Record for PipelineChart
  const statusCounts = (stats?.pipeline?.statuses ?? []).reduce(
    (acc, s) => {
      acc[s.status as OrderStatus] = s.count;
      return acc;
    },
    {} as Record<OrderStatus, number>,
  );

  if (statsLoading || ordersLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-muted-foreground">Načítání...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm sm:text-base text-muted-foreground">
          Přehled aktivních zakázek a zpráv
        </p>
      </div>

      <StatsCards
        totalOrders={stats?.total_orders ?? 0}
        inProduction={stats?.orders_in_production ?? 0}
        newMessages={stats?.new_inbox_messages ?? 0}
        pendingInvoices={stats?.pending_invoicing ?? 0}
      />

      <Recommendations />

      <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
        <PipelineChart statusCounts={statusCounts} />
        <div className="lg:col-span-2">
          <RecentOrders orders={recentOrders} />
        </div>
      </div>
    </div>
  );
}

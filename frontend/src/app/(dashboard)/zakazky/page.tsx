"use client";

import { NewOrderDialog } from "@/components/zakazky/new-order-dialog";
import { OrderFilters } from "@/components/zakazky/order-filters";
import { OrdersTable } from "@/components/zakazky/orders-table";
import { getOrders } from "@/lib/api";
import type { OrderStatus } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

export default function ZakazkyPage() {
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [skip] = useState(0);
  const [limit] = useState(50);

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders", { status: statusFilter, skip, limit }],
    queryFn: () =>
      getOrders({
        status: statusFilter !== "all" ? statusFilter : undefined,
        skip,
        limit,
      }),
  });

  // Client-side search filtering
  const filteredOrders = orders?.filter((order) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      order.number.toLowerCase().includes(query) ||
      order.customer?.company_name?.toLowerCase().includes(query) ||
      order.customer?.contact_name?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="flex h-full flex-col gap-4 sm:gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Zakázky</h1>
          <p className="text-sm sm:text-base text-muted-foreground">
            Přehled všech zakázek a objednávek
          </p>
        </div>
        <NewOrderDialog />
      </div>

      <OrderFilters
        statusFilter={statusFilter}
        onStatusChange={(value) => setStatusFilter(value)}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {isLoading ? (
        <div className="flex min-h-[400px] items-center justify-center rounded-lg border">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="mt-4 text-sm text-muted-foreground">
              Načítání zakázek...
            </p>
          </div>
        </div>
      ) : (
        <OrdersTable orders={filteredOrders || []} />
      )}
    </div>
  );
}

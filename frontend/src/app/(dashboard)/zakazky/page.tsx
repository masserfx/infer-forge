"use client";

import { NewOrderDialog } from "@/components/zakazky/new-order-dialog";
import { OrderFilters } from "@/components/zakazky/order-filters";
import { OrdersTable } from "@/components/zakazky/orders-table";
import { BulkActionBar } from "@/components/ui/bulk-action-bar";
import { Button } from "@/components/ui/button";
import { getOrders } from "@/lib/api";
import type { OrderStatus } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

export default function ZakazkyPage() {
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [quickFilter, setQuickFilter] = useState<string>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
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

  // Client-side search and quick filtering
  const filteredOrders = orders?.filter((order) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        order.number.toLowerCase().includes(query) ||
        order.customer?.company_name?.toLowerCase().includes(query) ||
        order.customer?.contact_name?.toLowerCase().includes(query);
      if (!matchesSearch) return false;
    }

    // Quick filter
    if (quickFilter === "all") return true;
    if (quickFilter === "overdue") return order.due_date && new Date(order.due_date) < new Date();
    if (quickFilter === "high") return order.priority === "high" || order.priority === "urgent";
    if (quickFilter === "unassigned") return !order.assigned_to;
    if (quickFilter === "poptavka") return order.status === "poptavka";
    return true;
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

      <div className="flex gap-2 flex-wrap">
        {[
          { key: "all", label: "Vše" },
          { key: "overdue", label: "Po termínu" },
          { key: "high", label: "Vysoká priorita" },
          { key: "unassigned", label: "Nepřiřazené" },
          { key: "poptavka", label: "Nové poptávky" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setQuickFilter(key)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              quickFilter === key
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-background text-muted-foreground border-border hover:border-primary/50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

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

      <BulkActionBar
        selectedCount={selectedIds.size}
        onClear={() => setSelectedIds(new Set())}
      >
        <Button size="sm" variant="outline" disabled>
          Změnit stav
        </Button>
        <Button size="sm" variant="outline" disabled>
          Přiřadit
        </Button>
      </BulkActionBar>
    </div>
  );
}

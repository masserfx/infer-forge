"use client";

import { useMemo, useState } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { getOrders, updateOrderStatus } from "@/lib/api";
import { stringToColor } from "@/lib/utils";
import type { Order, OrderStatus } from "@/types";
import { KanbanColumn } from "./kanban-column";
import { KanbanCard } from "./kanban-card";

const ORDER_STATUSES: OrderStatus[] = [
  "poptavka",
  "nabidka",
  "objednavka",
  "vyroba",
  "expedice",
  "fakturace",
  "dokonceno",
];

/** Valid status transitions (mirrors backend OrderService.STATUS_TRANSITIONS) */
const STATUS_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  poptavka: ["nabidka", "objednavka"],
  nabidka: ["objednavka", "poptavka"],
  objednavka: ["vyroba"],
  vyroba: ["expedice"],
  expedice: ["fakturace"],
  fakturace: ["dokonceno"],
  dokonceno: [],
};

const STATUS_BORDER_COLORS: Record<OrderStatus, string> = {
  poptavka: "border-t-blue-500",
  nabidka: "border-t-purple-500",
  objednavka: "border-t-yellow-500",
  vyroba: "border-t-orange-500",
  expedice: "border-t-cyan-500",
  fakturace: "border-t-green-500",
  dokonceno: "border-t-gray-500",
};

export function KanbanBoard() {
  const queryClient = useQueryClient();
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: () => getOrders({ limit: 1000 }),
  });

  // Extract unique customers for legend
  const customers = useMemo(() => {
    const map = new Map<string, { id: string; name: string; color: string; count: number }>();
    for (const order of orders) {
      const id = order.customer_id;
      const existing = map.get(id);
      if (existing) {
        existing.count++;
      } else {
        map.set(id, {
          id,
          name: order.customer?.company_name || "—",
          color: stringToColor(id),
          count: 1,
        });
      }
    }
    return Array.from(map.values()).sort((a, b) => b.count - a.count);
  }, [orders]);

  // Filter orders by selected customer
  const filteredOrders = useMemo(() => {
    if (!selectedCustomerId) return orders;
    return orders.filter((o) => o.customer_id === selectedCustomerId);
  }, [orders, selectedCustomerId]);

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: OrderStatus }) =>
      updateOrderStatus(id, status),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ["orders"] });
      const previousOrders = queryClient.getQueryData<Order[]>(["orders"]);

      queryClient.setQueryData<Order[]>(["orders"], (old) =>
        old?.map((order) =>
          order.id === id ? { ...order, status } : order
        ) || []
      );

      return { previousOrders };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousOrders) {
        queryClient.setQueryData(["orders"], context.previousOrders);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const handleDragStart = (event: DragStartEvent) => {
    const order = orders.find((o) => o.id === event.active.id);
    setActiveOrder(order || null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveOrder(null);

    if (!over) return;

    const orderId = active.id as string;
    const overId = over.id as string;

    // over.id can be a column status OR another card's UUID
    let newStatus: OrderStatus;
    if (ORDER_STATUSES.includes(overId as OrderStatus)) {
      newStatus = overId as OrderStatus;
    } else {
      // Dropped over a card — find which column it belongs to
      const overOrder = orders.find((o) => o.id === overId);
      if (!overOrder) return;
      newStatus = overOrder.status;
    }

    const order = orders.find((o) => o.id === orderId);
    if (!order || order.status === newStatus) return;

    // Validate transition before sending to backend
    const allowed = STATUS_TRANSITIONS[order.status] || [];
    if (!allowed.includes(newStatus)) return;

    updateStatusMutation.mutate({ id: orderId, status: newStatus });
  };

  const groupedOrders = ORDER_STATUSES.reduce(
    (acc, status) => {
      acc[status] = filteredOrders.filter((order) => order.status === status);
      return acc;
    },
    {} as Record<OrderStatus, Order[]>
  );

  if (isLoading) {
    return (
      <div className="flex h-[500px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Customer filter legend */}
      {customers.length > 1 && (
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setSelectedCustomerId(null)}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors border ${
              selectedCustomerId === null
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-background text-muted-foreground border-border hover:bg-muted"
            }`}
          >
            Vše ({orders.length})
          </button>
          {customers.map((c) => (
            <button
              key={c.id}
              onClick={() =>
                setSelectedCustomerId(selectedCustomerId === c.id ? null : c.id)
              }
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors border ${
                selectedCustomerId === c.id
                  ? "text-foreground border-current shadow-sm"
                  : "bg-background text-muted-foreground border-border hover:bg-muted"
              }`}
              style={
                selectedCustomerId === c.id
                  ? { borderColor: c.color, backgroundColor: `${c.color}15` }
                  : undefined
              }
            >
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: c.color }}
              />
              {c.name}
              <span className="text-muted-foreground">({c.count})</span>
            </button>
          ))}
        </div>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        {/* Mobile: vertical stacking */}
        <div className="md:hidden space-y-4">
          {ORDER_STATUSES.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              orders={groupedOrders[status]}
              borderColor={STATUS_BORDER_COLORS[status]}
            />
          ))}
        </div>

        {/* Tablet & Desktop: horizontal scroll with snap */}
        <div className="hidden md:flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory">
          {ORDER_STATUSES.map((status) => (
            <div key={status} className="snap-start">
              <KanbanColumn
                status={status}
                orders={groupedOrders[status]}
                borderColor={STATUS_BORDER_COLORS[status]}
              />
            </div>
          ))}
        </div>

        <DragOverlay>
          {activeOrder ? <KanbanCard order={activeOrder} /> : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

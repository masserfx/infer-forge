"use client";

import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Order, OrderStatus } from "@/types";
import { ORDER_STATUS_LABELS } from "@/types";
import { KanbanCard } from "./kanban-card";

interface KanbanColumnProps {
  status: OrderStatus;
  orders: Order[];
  borderColor: string;
}

export function KanbanColumn({ status, orders, borderColor }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: status,
  });

  return (
    <div
      className={`flex flex-col h-full w-80 flex-shrink-0 rounded-lg border-2 bg-muted/20 ${borderColor} ${
        isOver ? "bg-accent/50" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-2 p-4 border-b bg-background/95">
        <h3 className="font-semibold text-sm">{ORDER_STATUS_LABELS[status]}</h3>
        <Badge variant="secondary" className="rounded-full">
          {orders.length}
        </Badge>
      </div>

      <ScrollArea className="flex-1">
        <div ref={setNodeRef} className="p-4 min-h-[500px]">
          <SortableContext
            items={orders.map((o) => o.id)}
            strategy={verticalListSortingStrategy}
          >
            {orders.length === 0 ? (
              <div className="flex h-40 items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25">
                <p className="text-sm text-muted-foreground">
                  Přetáhněte sem
                </p>
              </div>
            ) : (
              orders.map((order) => <KanbanCard key={order.id} order={order} />)
            )}
          </SortableContext>
        </div>
      </ScrollArea>
    </div>
  );
}

"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useRouter } from "next/navigation";
import { Calendar, Package } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Order } from "@/types";
import { PRIORITY_LABELS, PRIORITY_COLORS } from "@/types";

interface KanbanCardProps {
  order: Order;
}

export function KanbanCard({ order }: KanbanCardProps) {
  const router = useRouter();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: order.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleClick = () => {
    router.push(`/zakazky/${order.id}`);
  };

  const dueDate = order.due_date ? new Date(order.due_date) : null;
  const isOverdue =
    dueDate && dueDate < new Date() && order.status !== "dokonceno";

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        className="mb-3 cursor-pointer transition-all hover:shadow-md"
        onClick={handleClick}
      >
        <CardContent className="p-4">
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{order.number}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {order.customer?.company_name || "—"}
                </p>
              </div>
              <Badge
                variant="secondary"
                className={PRIORITY_COLORS[order.priority]}
              >
                {PRIORITY_LABELS[order.priority]}
              </Badge>
            </div>

            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Package className="h-3 w-3" />
                <span>{order.items.length}</span>
              </div>
              {dueDate && (
                <div
                  className={`flex items-center gap-1 ${isOverdue ? "text-destructive font-medium" : ""}`}
                >
                  <Calendar className="h-3 w-3" />
                  <span>
                    {dueDate.toLocaleDateString("cs-CZ", {
                      day: "numeric",
                      month: "short",
                    })}
                  </span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

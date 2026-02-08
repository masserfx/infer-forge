"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useRouter } from "next/navigation";
import { Calendar, Package, UserCheck, UserPlus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { assignOrder } from "@/lib/api";
import { useAuth } from "@/lib/auth-provider";
import type { Order } from "@/types";
import { PRIORITY_LABELS, PRIORITY_COLORS } from "@/types";

interface KanbanCardProps {
  order: Order;
}

export function KanbanCard({ order }: KanbanCardProps) {
  const router = useRouter();
  const { user } = useAuth();
  const queryClient = useQueryClient();
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

  const assignMutation = useMutation({
    mutationFn: () => assignOrder(order.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const handleClick = () => {
    router.push(`/zakazky/${order.id}`);
  };

  const handleAssign = (e: React.MouseEvent) => {
    e.stopPropagation();
    assignMutation.mutate();
  };

  const dueDate = order.due_date ? new Date(order.due_date) : null;
  const isOverdue =
    dueDate && dueDate < new Date() && order.status !== "dokonceno";

  const isAssignedToMe = order.assigned_to === user?.id;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="touch-manipulation"
    >
      <Card
        className="mb-3 cursor-pointer transition-all hover:shadow-md min-h-[44px]"
        onClick={handleClick}
      >
        <CardContent className="p-3 sm:p-4">
          <div className="space-y-2 sm:space-y-3">
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

            <div className="flex items-center gap-3 sm:gap-4 text-xs text-muted-foreground">
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

            {/* Assignment status */}
            {order.assigned_to_name ? (
              <div className="flex items-center gap-1.5">
                <div
                  className={`flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold ${
                    isAssignedToMe
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {order.assigned_to_name.charAt(0).toUpperCase()}
                </div>
                <span className="text-xs text-muted-foreground truncate">
                  {isAssignedToMe ? "Vy" : order.assigned_to_name}
                </span>
                {isAssignedToMe && (
                  <UserCheck className="h-3 w-3 text-primary ml-auto" />
                )}
              </div>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-full text-xs text-muted-foreground hover:text-primary"
                onClick={handleAssign}
                disabled={assignMutation.isPending}
              >
                <UserPlus className="h-3 w-3 mr-1" />
                {assignMutation.isPending ? "Přiřazuji..." : "Převzít"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

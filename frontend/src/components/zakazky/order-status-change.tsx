"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { updateOrderStatus } from "@/lib/api";
import { ORDER_STATUS_LABELS, type OrderStatus } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

interface OrderStatusChangeProps {
  orderId: string;
  currentStatus: OrderStatus;
}

export function OrderStatusChange({
  orderId,
  currentStatus,
}: OrderStatusChangeProps) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (status: OrderStatus) => updateOrderStatus(orderId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["order", orderId] });
      toast.success("Stav zakázky byl úspěšně změněn");
    },
    onError: (error) => {
      toast.error(`Chyba při změně stavu: ${error.message}`);
    },
  });

  return (
    <Select
      value={currentStatus}
      onValueChange={(value) => mutation.mutate(value as OrderStatus)}
      disabled={mutation.isPending}
    >
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => (
          <SelectItem key={value} value={value}>
            {label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

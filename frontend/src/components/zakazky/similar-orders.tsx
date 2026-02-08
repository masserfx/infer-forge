"use client";

import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import Link from "next/link";
import { getSimilarOrders } from "@/lib/api";
import { ORDER_STATUS_LABELS, PRIORITY_LABELS } from "@/types";
import { Badge } from "@/components/ui/badge";

interface SimilarOrdersProps {
  orderId: string;
}

export function SimilarOrders({ orderId }: SimilarOrdersProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["similar-orders", orderId],
    queryFn: () => getSimilarOrders(orderId),
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-5 w-5 text-muted-foreground" />
          <h3 className="font-semibold">Podobné zakázky</h3>
        </div>
        <div className="animate-pulse space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-muted rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.similar_orders.length === 0) {
    return (
      <div className="rounded-lg border p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-5 w-5 text-muted-foreground" />
          <h3 className="font-semibold">Podobné zakázky</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Žádné podobné zakázky nenalezeny
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-5 w-5 text-purple-500" />
        <h3 className="font-semibold">Podobné zakázky</h3>
        <Badge variant="secondary" className="text-xs">
          AI
        </Badge>
      </div>
      <div className="space-y-2">
        {data.similar_orders.map((order) => (
          <Link
            key={order.order_id}
            href={`/zakazky/${order.order_id}`}
            className="flex items-center justify-between rounded-md border p-3 hover:bg-accent transition-colors"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">
                  {order.order_number}
                </span>
                <Badge variant="outline" className="text-xs">
                  {ORDER_STATUS_LABELS[order.status as keyof typeof ORDER_STATUS_LABELS] || order.status}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {PRIORITY_LABELS[order.priority as keyof typeof PRIORITY_LABELS] || order.priority}
                </Badge>
              </div>
              {order.customer_name && (
                <p className="text-xs text-muted-foreground mt-1">
                  {order.customer_name}
                </p>
              )}
            </div>
            <div className="text-right">
              <span className="text-sm font-medium text-purple-600">
                {Math.round(order.similarity * 100)}%
              </span>
              <p className="text-xs text-muted-foreground">shoda</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  type OrderStatus,
} from "@/types";

interface PipelineChartProps {
  statusCounts: Record<OrderStatus, number>;
}

export function PipelineChart({ statusCounts }: PipelineChartProps) {
  const statuses: OrderStatus[] = [
    "poptavka",
    "nabidka",
    "objednavka",
    "vyroba",
    "expedice",
    "fakturace",
    "dokonceno",
  ];

  const total = Object.values(statusCounts).reduce((acc, count) => acc + count, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline přehled</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {statuses.map((status) => {
            const count = statusCounts[status] || 0;
            const percentage = total > 0 ? (count / total) * 100 : 0;

            return (
              <div key={status} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="secondary"
                      className={ORDER_STATUS_COLORS[status]}
                    >
                      {ORDER_STATUS_LABELS[status]}
                    </Badge>
                  </div>
                  <span className="font-medium">{count}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

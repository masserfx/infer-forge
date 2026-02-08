"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ORDER_STATUS_COLORS,
  ORDER_STATUS_LABELS,
  PRIORITY_COLORS,
  PRIORITY_LABELS,
  type Order,
} from "@/types";
import { useRouter } from "next/navigation";
import { Calendar, User } from "lucide-react";

interface OrdersTableProps {
  orders: Order[];
}

export function OrdersTable({ orders }: OrdersTableProps) {
  const router = useRouter();

  if (orders.length === 0) {
    return (
      <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-dashed">
        <div className="text-center">
          <p className="text-base sm:text-lg font-medium text-muted-foreground">
            Žádné zakázky
          </p>
          <p className="text-sm text-muted-foreground">
            Zkuste změnit filtry nebo vytvořit novou zakázku
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Mobile: Card layout */}
      <div className="md:hidden space-y-3">
        {orders.map((order) => (
          <Card
            key={order.id}
            className="cursor-pointer transition-all hover:shadow-md min-h-[44px]"
            onClick={() => router.push(`/zakazky/${order.id}`)}
          >
            <CardContent className="p-4">
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm truncate">{order.number}</p>
                    <div className="flex items-center gap-1 mt-1">
                      <User className="h-3 w-3 text-muted-foreground" />
                      <p className="text-xs text-muted-foreground truncate">
                        {order.customer?.company_name || "—"}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant="secondary"
                    className={PRIORITY_COLORS[order.priority]}
                  >
                    {PRIORITY_LABELS[order.priority]}
                  </Badge>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <Badge
                    variant="secondary"
                    className={ORDER_STATUS_COLORS[order.status]}
                  >
                    {ORDER_STATUS_LABELS[order.status]}
                  </Badge>
                  {order.due_date && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      <span>
                        {new Date(order.due_date).toLocaleDateString("cs-CZ", {
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
        ))}
      </div>

      {/* Tablet & Desktop: Table with horizontal scroll */}
      <div className="hidden md:block rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-[120px]">Číslo zakázky</TableHead>
              <TableHead className="min-w-[150px]">Zákazník</TableHead>
              <TableHead className="min-w-[120px]">Stav</TableHead>
              <TableHead className="min-w-[100px]">Priorita</TableHead>
              <TableHead className="min-w-[100px]">Termín</TableHead>
              <TableHead className="min-w-[100px]">Vytvořeno</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.map((order) => (
              <TableRow
                key={order.id}
                onClick={() => router.push(`/zakazky/${order.id}`)}
                className="cursor-pointer min-h-[44px]"
              >
                <TableCell className="font-medium">{order.number}</TableCell>
                <TableCell>
                  {order.customer?.company_name || "—"}
                  {order.customer?.contact_name && (
                    <span className="block text-sm text-muted-foreground">
                      {order.customer.contact_name}
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={ORDER_STATUS_COLORS[order.status]}
                  >
                    {ORDER_STATUS_LABELS[order.status]}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={PRIORITY_COLORS[order.priority]}
                  >
                    {PRIORITY_LABELS[order.priority]}
                  </Badge>
                </TableCell>
                <TableCell>
                  {order.due_date
                    ? new Date(order.due_date).toLocaleDateString("cs-CZ")
                    : "—"}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(order.created_at).toLocaleDateString("cs-CZ")}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

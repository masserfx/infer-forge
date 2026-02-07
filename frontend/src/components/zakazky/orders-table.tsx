"use client";

import { Badge } from "@/components/ui/badge";
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

interface OrdersTableProps {
  orders: Order[];
}

export function OrdersTable({ orders }: OrdersTableProps) {
  const router = useRouter();

  if (orders.length === 0) {
    return (
      <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-dashed">
        <div className="text-center">
          <p className="text-lg font-medium text-muted-foreground">
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
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Číslo zakázky</TableHead>
            <TableHead>Zákazník</TableHead>
            <TableHead>Stav</TableHead>
            <TableHead>Priorita</TableHead>
            <TableHead>Termín</TableHead>
            <TableHead>Vytvořeno</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map((order) => (
            <TableRow
              key={order.id}
              onClick={() => router.push(`/zakazky/${order.id}`)}
              className="cursor-pointer"
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
  );
}

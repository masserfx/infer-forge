"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  PRIORITY_LABELS,
  PRIORITY_COLORS,
  type Order,
} from "@/types";

interface RecentOrdersProps {
  orders: Order[];
}

export function RecentOrders({ orders }: RecentOrdersProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base sm:text-lg">Poslední zakázky</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-[100px]">Číslo</TableHead>
              <TableHead className="min-w-[150px]">Zákazník</TableHead>
              <TableHead className="min-w-[120px]">Stav</TableHead>
              <TableHead className="min-w-[100px]">Priorita</TableHead>
              <TableHead className="min-w-[100px]">Datum</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  Žádné zakázky
                </TableCell>
              </TableRow>
            ) : (
              orders.map((order) => (
                <TableRow key={order.id} className="min-h-[44px]">
                  <TableCell>
                    <Link
                      href={`/zakazky/${order.id}`}
                      className="font-medium hover:underline"
                    >
                      {order.number}
                    </Link>
                  </TableCell>
                  <TableCell className="text-xs sm:text-sm">
                    {order.customer?.company_name || "—"}
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
                  <TableCell className="text-xs sm:text-sm text-muted-foreground">
                    {new Date(order.created_at).toLocaleDateString("cs-CZ")}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

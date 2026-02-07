"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { OrderItem } from "@/types";

interface OrderItemsTableProps {
  items: OrderItem[];
}

export function OrderItemsTable({ items }: OrderItemsTableProps) {
  if (items.length === 0) {
    return (
      <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed">
        <p className="text-sm text-muted-foreground">Žádné položky</p>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Název</TableHead>
            <TableHead>Materiál</TableHead>
            <TableHead className="text-center">DN</TableHead>
            <TableHead className="text-center">PN</TableHead>
            <TableHead className="text-right">Množství</TableHead>
            <TableHead>Jednotka</TableHead>
            <TableHead>Poznámka</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="font-medium">{item.name}</TableCell>
              <TableCell>{item.material || "—"}</TableCell>
              <TableCell className="text-center">{item.dn || "—"}</TableCell>
              <TableCell className="text-center">{item.pn || "—"}</TableCell>
              <TableCell className="text-right">{item.quantity}</TableCell>
              <TableCell>{item.unit}</TableCell>
              <TableCell className="max-w-[300px] truncate text-muted-foreground">
                {item.note || "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

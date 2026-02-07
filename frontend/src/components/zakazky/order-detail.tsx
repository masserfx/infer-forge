"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { syncEntity, getSyncLogs } from "@/lib/api";
import {
  ORDER_STATUS_COLORS,
  ORDER_STATUS_LABELS,
  PRIORITY_COLORS,
  PRIORITY_LABELS,
  type Order,
} from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, RefreshCw, Building2, Mail, FileText } from "lucide-react";
import { toast } from "sonner";
import { OrderStatusChange } from "./order-status-change";

interface OrderDetailProps {
  order: Order;
}

export function OrderDetail({ order }: OrderDetailProps) {
  const queryClient = useQueryClient();

  const { data: syncLogs } = useQuery({
    queryKey: ["sync-logs", order.id],
    queryFn: () => getSyncLogs({ entity_type: "order", entity_id: order.id }),
  });

  const syncMutation = useMutation({
    mutationFn: () => syncEntity("order", order.id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["sync-logs", order.id] });
      queryClient.invalidateQueries({ queryKey: ["order", order.id] });
      if (data.success) {
        toast.success("Synchronizace s Pohodou byla úspěšná");
      } else {
        toast.error(`Chyba při synchronizaci: ${data.error}`);
      }
    },
    onError: (error) => {
      toast.error(`Chyba při synchronizaci: ${error.message}`);
    },
  });

  const lastSync = syncLogs?.[0];

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Informace o zakázce
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              Zákazník
            </p>
            <p className="text-lg font-semibold">
              {order.customer?.company_name || "—"}
            </p>
            {order.customer?.contact_name && (
              <p className="text-sm text-muted-foreground">
                {order.customer.contact_name}
              </p>
            )}
          </div>

          {order.customer?.ico && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">IČO</p>
              <p className="text-sm">{order.customer.ico}</p>
            </div>
          )}

          {order.customer?.email && (
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <a
                href={`mailto:${order.customer.email}`}
                className="text-sm text-primary hover:underline"
              >
                {order.customer.email}
              </a>
            </div>
          )}

          <Separator />

          <div>
            <p className="text-sm font-medium text-muted-foreground">
              Priorita
            </p>
            <Badge
              variant="secondary"
              className={`mt-1 ${PRIORITY_COLORS[order.priority]}`}
            >
              {PRIORITY_LABELS[order.priority]}
            </Badge>
          </div>

          {order.due_date && (
            <div className="flex items-center gap-2">
              <CalendarDays className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Termín dodání
                </p>
                <p className="text-sm">
                  {new Date(order.due_date).toLocaleDateString("cs-CZ", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </p>
              </div>
            </div>
          )}

          {order.note && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Poznámka
              </p>
              <p className="text-sm">{order.note}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Stav a synchronizace
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="mb-2 text-sm font-medium text-muted-foreground">
              Stav zakázky
            </p>
            <div className="flex items-center gap-3">
              <Badge
                variant="secondary"
                className={ORDER_STATUS_COLORS[order.status]}
              >
                {ORDER_STATUS_LABELS[order.status]}
              </Badge>
              <div className="flex-1">
                <OrderStatusChange
                  orderId={order.id}
                  currentStatus={order.status}
                />
              </div>
            </div>
          </div>

          <Separator />

          <div>
            <p className="mb-2 text-sm font-medium text-muted-foreground">
              Synchronizace s Pohodou
            </p>
            <Button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              variant="outline"
              className="w-full"
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${syncMutation.isPending ? "animate-spin" : ""}`}
              />
              {syncMutation.isPending
                ? "Synchronizuji..."
                : "Synchronizovat s Pohodou"}
            </Button>

            {lastSync && (
              <div className="mt-3 rounded-lg bg-muted p-3">
                <p className="text-sm font-medium">Poslední synchronizace</p>
                <p className="text-xs text-muted-foreground">
                  {new Date(lastSync.synced_at).toLocaleString("cs-CZ")}
                </p>
                {lastSync.status === "success" && (
                  <p className="mt-1 text-xs text-green-600">
                    Úspěšně synchronizováno
                    {lastSync.pohoda_doc_number &&
                      ` (číslo dokladu: ${lastSync.pohoda_doc_number})`}
                  </p>
                )}
                {lastSync.status === "error" && (
                  <p className="mt-1 text-xs text-red-600">
                    Chyba: {lastSync.error_message}
                  </p>
                )}
              </div>
            )}

            {order.pohoda_id && (
              <div className="mt-2">
                <p className="text-xs text-muted-foreground">
                  Pohoda ID: {order.pohoda_id}
                </p>
              </div>
            )}
          </div>

          <Separator />

          <div className="space-y-1 text-xs text-muted-foreground">
            <p>
              Vytvořeno: {new Date(order.created_at).toLocaleString("cs-CZ")}
            </p>
            <p>
              Aktualizováno:{" "}
              {new Date(order.updated_at).toLocaleString("cs-CZ")}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

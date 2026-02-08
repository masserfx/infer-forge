"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getSyncLogs,
  getCustomers,
  getOrders,
  syncEntity,
  syncPohodaInventory,
} from "@/lib/api";
import type { Customer, Order, PohodaSyncLog } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  Upload,
  Download,
  Users,
  Package,
  Loader2,
  Warehouse,
} from "lucide-react";
import { useState } from "react";
import { format } from "date-fns";
import { cs } from "date-fns/locale/cs";
import { toast } from "sonner";

const STATUS_CONFIG = {
  pending: { label: "Čeká", icon: Clock, color: "bg-yellow-100 text-yellow-800" },
  success: { label: "Úspěch", icon: CheckCircle, color: "bg-green-100 text-green-800" },
  error: { label: "Chyba", icon: XCircle, color: "bg-red-100 text-red-800" },
};

const DIRECTION_LABELS: Record<string, string> = {
  export: "Export do Pohody",
  import: "Import z Pohody",
};

const ENTITY_LABELS: Record<string, string> = {
  order: "Zakázka",
  customer: "Zákazník",
  invoice: "Faktura",
  offer: "Nabídka",
};

export default function PohodaPage() {
  const queryClient = useQueryClient();
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>("all");
  const [syncingCustomer, setSyncingCustomer] = useState<string | null>(null);
  const [syncingOrder, setSyncingOrder] = useState<string | null>(null);
  const [syncingInventory, setSyncingInventory] = useState(false);

  const { data: logs = [], isLoading } = useQuery<PohodaSyncLog[]>({
    queryKey: ["pohoda-logs", entityTypeFilter],
    queryFn: () =>
      getSyncLogs(
        entityTypeFilter !== "all" ? { entity_type: entityTypeFilter } : undefined,
      ),
  });

  const { data: customers = [] } = useQuery<Customer[]>({
    queryKey: ["customers"],
    queryFn: getCustomers,
  });

  const { data: orders = [] } = useQuery<Order[]>({
    queryKey: ["orders"],
    queryFn: () => getOrders({ limit: 100 }),
  });

  const refreshLogs = () => {
    queryClient.invalidateQueries({ queryKey: ["pohoda-logs"] });
  };

  const handleSyncCustomer = async (customerId: string) => {
    setSyncingCustomer(customerId);
    try {
      const result = await syncEntity("customer", customerId);
      if (result.success) {
        toast.success("Zákazník synchronizován do Pohody", {
          description: `Pohoda ID: ${result.pohoda_doc_number || result.pohoda_id}`,
        });
      } else {
        toast.error("Synchronizace selhala", {
          description: result.error || "Neznámá chyba",
        });
      }
      refreshLogs();
    } catch (err) {
      toast.error("Chyba při synchronizaci", {
        description: err instanceof Error ? err.message : "Neznámá chyba",
      });
    } finally {
      setSyncingCustomer(null);
    }
  };

  const handleSyncOrder = async (orderId: string) => {
    setSyncingOrder(orderId);
    try {
      const result = await syncEntity("order", orderId);
      if (result.success) {
        toast.success("Zakázka synchronizována do Pohody", {
          description: `Pohoda ID: ${result.pohoda_doc_number || result.pohoda_id}`,
        });
      } else {
        toast.error("Synchronizace selhala", {
          description: result.error || "Neznámá chyba",
        });
      }
      refreshLogs();
    } catch (err) {
      toast.error("Chyba při synchronizaci", {
        description: err instanceof Error ? err.message : "Neznámá chyba",
      });
    } finally {
      setSyncingOrder(null);
    }
  };

  const handleSyncInventory = async () => {
    setSyncingInventory(true);
    try {
      const result = await syncPohodaInventory();
      toast.success("Import skladu dokončen", {
        description: `Vytvořeno: ${result.created}, aktualizováno: ${result.updated}, chyb: ${result.errors}`,
      });
      refreshLogs();
    } catch (err) {
      toast.error("Chyba při importu skladu", {
        description: err instanceof Error ? err.message : "Neznámá chyba",
      });
    } finally {
      setSyncingInventory(false);
    }
  };

  const sortedLogs = [...logs].sort(
    (a, b) => new Date(b.synced_at).getTime() - new Date(a.synced_at).getTime(),
  );

  const successCount = logs.filter((l) => l.status === "success").length;
  const errorCount = logs.filter((l) => l.status === "error").length;
  const pendingCount = logs.filter((l) => l.status === "pending").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Pohoda</h1>
        <p className="text-muted-foreground">
          Synchronizace s účetním systémem Pohoda
        </p>
      </div>

      {/* Sync actions panel */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Sync customer */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-blue-600" />
            <h3 className="font-semibold text-sm">Export zákazníka</h3>
          </div>
          <div className="flex gap-2">
            <Select
              value={syncingCustomer === null ? "" : ""}
              onValueChange={(val) => handleSyncCustomer(val)}
            >
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Vyberte zákazníka" />
              </SelectTrigger>
              <SelectContent>
                {customers.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.company_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {syncingCustomer && (
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mt-2" />
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Odešle zákazníka do adresáře Pohody (adb:addressbook)
          </p>
        </div>

        {/* Sync order */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5 text-orange-600" />
            <h3 className="font-semibold text-sm">Export zakázky</h3>
          </div>
          <div className="flex gap-2">
            <Select
              value=""
              onValueChange={(val) => handleSyncOrder(val)}
            >
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Vyberte zakázku" />
              </SelectTrigger>
              <SelectContent>
                {orders.map((o) => (
                  <SelectItem key={o.id} value={o.id}>
                    {o.number} — {o.customer?.company_name || "bez zákazníka"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {syncingOrder && (
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mt-2" />
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Odešle zakázku do Pohody (ord:order)
          </p>
        </div>

        {/* Import inventory */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Warehouse className="h-5 w-5 text-green-600" />
            <h3 className="font-semibold text-sm">Import skladu</h3>
          </div>
          <Button
            variant="outline"
            className="w-full"
            onClick={handleSyncInventory}
            disabled={syncingInventory}
          >
            {syncingInventory ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            Importovat skladové karty
          </Button>
          <p className="text-xs text-muted-foreground">
            Stáhne materiálové ceny ze skladu Pohody (lStk:listStock)
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span className="text-sm text-muted-foreground">Úspěšné</span>
          </div>
          <p className="mt-2 text-2xl font-bold">{successCount}</p>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-600" />
            <span className="text-sm text-muted-foreground">Chybové</span>
          </div>
          <p className="mt-2 text-2xl font-bold">{errorCount}</p>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-yellow-600" />
            <span className="text-sm text-muted-foreground">Čekající</span>
          </div>
          <p className="mt-2 text-2xl font-bold">{pendingCount}</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Historie synchronizací</h2>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={refreshLogs}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Select value={entityTypeFilter} onValueChange={setEntityTypeFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Typ entity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Všechny typy</SelectItem>
              <SelectItem value="order">Zakázky</SelectItem>
              <SelectItem value="customer">Zákazníci</SelectItem>
              <SelectItem value="invoice">Faktury</SelectItem>
              <SelectItem value="offer">Nabídky</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-lg border bg-card">
        {isLoading ? (
          <div className="flex items-center justify-center p-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : sortedLogs.length === 0 ? (
          <div className="p-8 text-center">
            <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-sm font-medium">Žádné synchronizace</p>
            <p className="text-sm text-muted-foreground">
              Použijte panel výše pro synchronizaci zákazníků, zakázek nebo import skladu
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium">Stav</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Směr</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Entita</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Číslo dokladu</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Datum</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Chyba</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {sortedLogs.map((log) => {
                  const statusCfg = STATUS_CONFIG[log.status];
                  const StatusIcon = statusCfg.icon;

                  return (
                    <tr key={log.id} className="hover:bg-muted/30">
                      <td className="px-4 py-3 text-sm">
                        <Badge variant="secondary" className={statusCfg.color}>
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {statusCfg.label}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {DIRECTION_LABELS[log.direction] || log.direction}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex flex-col">
                          <span className="font-medium">
                            {ENTITY_LABELS[log.entity_type] || log.entity_type}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {log.entity_id.slice(0, 8)}...
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm font-mono">
                        {log.pohoda_doc_number || "—"}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {format(new Date(log.synced_at), "d. M. yyyy HH:mm", {
                          locale: cs,
                        })}
                      </td>
                      <td className="px-4 py-3 text-sm text-red-600">
                        {log.error_message || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

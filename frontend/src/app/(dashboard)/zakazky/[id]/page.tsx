"use client";

import { OrderDetail } from "@/components/zakazky/order-detail";
import { OrderItemsTable } from "@/components/zakazky/order-items-table";
import { OrderDocuments } from "@/components/zakazky/order-documents";
import { OrderCalculations } from "@/components/zakazky/order-calculations";
import { OrderOperations } from "@/components/zakazky/order-operations";
import { SimilarOrders } from "@/components/zakazky/similar-orders";
import { DocumentGenerator } from "@/components/zakazky/document-generator";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { getOrder, assignOrder } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Package, UserPlus, UserCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { use } from "react";
import { useAuth } from "@/lib/auth-provider";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function OrderDetailPage({ params }: PageProps) {
  const router = useRouter();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const resolvedParams = use(params);

  const { data: order, isLoading } = useQuery({
    queryKey: ["order", resolvedParams.id],
    queryFn: () => getOrder(resolvedParams.id),
  });

  const assignMutation = useMutation({
    mutationFn: () => assignOrder(resolvedParams.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["order", resolvedParams.id] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const isAssignedToMe = order?.assigned_to === user?.id;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-4 text-sm text-muted-foreground">
            Načítání zakázky...
          </p>
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="text-center">
          <p className="text-lg font-medium">Zakázka nenalezena</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => router.push("/zakazky")}
          >
            Zpět na seznam zakázek
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/zakazky")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Zakázka {order.number}
            </h1>
            <p className="text-muted-foreground">
              Detail zakázky a přehled položek
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {order.assigned_to_name ? (
            <div className="flex items-center gap-2 text-sm">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full font-bold text-xs ${
                  isAssignedToMe
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {order.assigned_to_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="font-medium">
                  {isAssignedToMe ? "Převzato vámi" : order.assigned_to_name}
                </p>
                <p className="text-xs text-muted-foreground">Přiřazeno</p>
              </div>
              {isAssignedToMe && (
                <UserCheck className="h-4 w-4 text-primary" />
              )}
            </div>
          ) : (
            <Button
              onClick={() => assignMutation.mutate()}
              disabled={assignMutation.isPending}
              variant="default"
            >
              <UserPlus className="h-4 w-4 mr-2" />
              {assignMutation.isPending ? "Přiřazuji..." : "Převzít zakázku"}
            </Button>
          )}
        </div>
      </div>

      <OrderDetail order={order} />

      <Separator className="my-2" />

      <div>
        <div className="mb-4 flex items-center gap-2">
          <Package className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Položky zakázky</h2>
          <span className="text-sm text-muted-foreground">
            ({order.items.length})
          </span>
        </div>
        <OrderItemsTable items={order.items} />
      </div>

      <Separator className="my-2" />

      <OrderCalculations orderId={order.id} />

      <Separator className="my-2" />

      <OrderOperations orderId={order.id} />

      <Separator className="my-2" />

      <OrderDocuments entityType="order" entityId={order.id} />

      <Separator className="my-2" />

      <div className="grid gap-4 lg:grid-cols-2">
        <DocumentGenerator orderId={order.id} />
        <SimilarOrders orderId={order.id} />
      </div>
    </div>
  );
}

"use client";

import { OrderDetail } from "@/components/zakazky/order-detail";
import { OrderItemsTable } from "@/components/zakazky/order-items-table";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { getOrder } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Package } from "lucide-react";
import { useRouter } from "next/navigation";
import { use } from "react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function OrderDetailPage({ params }: PageProps) {
  const router = useRouter();
  const resolvedParams = use(params);

  const { data: order, isLoading } = useQuery({
    queryKey: ["order", resolvedParams.id],
    queryFn: () => getOrder(resolvedParams.id),
  });

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
    </div>
  );
}

"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { createCalculation, getCalculations, getOrders } from "@/lib/api";
import {
  CALCULATION_STATUS_LABELS,
  type CalculationStatus,
} from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calculator, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { formatCurrency } from "@/lib/utils";

export default function KalkulacePage() {
  const [statusFilter, setStatusFilter] = useState<
    CalculationStatus | "all"
  >("all");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: calculations, isLoading } = useQuery({
    queryKey: ["calculations", { status: statusFilter }],
    queryFn: () =>
      getCalculations({
        status: statusFilter !== "all" ? statusFilter : undefined,
      }),
  });

  const { data: orders } = useQuery({
    queryKey: ["orders"],
    queryFn: () => getOrders({}),
  });

  const createMutation = useMutation({
    mutationFn: createCalculation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calculations"] });
      setIsCreateDialogOpen(false);
    },
  });

  const [formData, setFormData] = useState({
    order_id: "",
    name: "",
    margin_percent: 20,
    note: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      order_id: formData.order_id,
      name: formData.name,
      margin_percent: formData.margin_percent,
      note: formData.note || undefined,
    });
  };

  const getStatusBadgeVariant = (
    status: CalculationStatus,
  ): "default" | "secondary" | "outline" => {
    switch (status) {
      case "draft":
        return "outline";
      case "approved":
        return "default";
      case "offered":
        return "secondary";
      default:
        return "outline";
    }
  };

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Kalkulace</h1>
          <p className="text-muted-foreground">
            Přehled cenových kalkulací pro zakázky
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Nová kalkulace
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={handleSubmit}>
              <DialogHeader>
                <DialogTitle>Nová kalkulace</DialogTitle>
                <DialogDescription>
                  Vytvořte novou cenovou kalkulaci pro zakázku
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="order_id">Zakázka *</Label>
                  <Select
                    value={formData.order_id}
                    onValueChange={(value) =>
                      setFormData({ ...formData, order_id: value })
                    }
                    required
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Vyberte zakázku" />
                    </SelectTrigger>
                    <SelectContent>
                      {orders?.map((order) => (
                        <SelectItem key={order.id} value={order.id}>
                          {order.number} - {order.customer?.company_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Název kalkulace *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder="např. Standardní kalkulace"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="margin_percent">Marže (%)</Label>
                  <Input
                    id="margin_percent"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formData.margin_percent}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        margin_percent: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="note">Poznámka</Label>
                  <Textarea
                    id="note"
                    value={formData.note}
                    onChange={(e) =>
                      setFormData({ ...formData, note: e.target.value })
                    }
                    placeholder="Interní poznámky k kalkulaci..."
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Zrušit
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Vytváření..." : "Vytvořit"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex items-center gap-4">
        <Select
          value={statusFilter}
          onValueChange={(value) =>
            setStatusFilter(value as CalculationStatus | "all")
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Všechny stavy</SelectItem>
            <SelectItem value="draft">Koncept</SelectItem>
            <SelectItem value="approved">Schváleno</SelectItem>
            <SelectItem value="offered">Nabídnuto</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="flex min-h-[400px] items-center justify-center rounded-lg border">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
            <p className="mt-4 text-sm text-muted-foreground">
              Načítání kalkulací...
            </p>
          </div>
        </div>
      ) : calculations && calculations.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {calculations.map((calc) => (
            <Link key={calc.id} href={`/kalkulace/${calc.id}`}>
              <Card className="hover:bg-accent transition-colors cursor-pointer h-full">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <Calculator className="h-5 w-5 text-muted-foreground" />
                    <Badge variant={getStatusBadgeVariant(calc.status)}>
                      {CALCULATION_STATUS_LABELS[calc.status]}
                    </Badge>
                  </div>
                  <CardTitle className="text-xl">{calc.name}</CardTitle>
                  <CardDescription>
                    Zakázka:{" "}
                    {orders?.find((o) => o.id === calc.order_id)?.number}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        Celková cena:
                      </span>
                      <span className="font-semibold">
                        {formatCurrency(calc.total_price)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Marže:</span>
                      <span>
                        {calc.margin_percent}% (
                        {formatCurrency(calc.margin_amount)})
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Položek:</span>
                      <span>{calc.items.length}</span>
                    </div>
                    <div className="pt-2 text-xs text-muted-foreground">
                      {new Date(calc.created_at).toLocaleDateString("cs-CZ")}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Calculator className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-2">Žádné kalkulace</p>
            <p className="text-sm text-muted-foreground mb-4">
              {statusFilter === "all"
                ? "Zatím nebyly vytvořeny žádné kalkulace"
                : "Pro vybraný stav nejsou k dispozici žádné kalkulace"}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

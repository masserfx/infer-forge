"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getOrderCalculations } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { CALCULATION_STATUS_LABELS, type CalculationStatus } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { Calculator, ExternalLink } from "lucide-react";
import Link from "next/link";

interface OrderCalculationsProps {
  orderId: string;
}

export function OrderCalculations({ orderId }: OrderCalculationsProps) {
  const { data: calculations, isLoading } = useQuery({
    queryKey: ["calculations", "order", orderId],
    queryFn: () => getOrderCalculations(orderId),
  });

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
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Calculator className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-xl font-semibold">Kalkulace</h2>
        {calculations && calculations.length > 0 && (
          <span className="text-sm text-muted-foreground">
            ({calculations.length})
          </span>
        )}
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
              <p className="mt-2 text-sm text-muted-foreground">
                Načítání kalkulací...
              </p>
            </div>
          </CardContent>
        </Card>
      ) : calculations && calculations.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {calculations.map((calc) => (
            <Card key={calc.id} className="hover:bg-accent transition-colors">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg">{calc.name}</CardTitle>
                  <Badge variant={getStatusBadgeVariant(calc.status)}>
                    {CALCULATION_STATUS_LABELS[calc.status]}
                  </Badge>
                </div>
                <CardDescription>
                  {new Date(calc.created_at).toLocaleDateString("cs-CZ")}
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
                      {calc.margin_percent}% ({formatCurrency(calc.margin_amount)})
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Položek:</span>
                    <span>{calc.items.length}</span>
                  </div>
                  <div className="pt-2">
                    <Button variant="outline" size="sm" className="w-full" asChild>
                      <Link href={`/kalkulace/${calc.id}`}>
                        Detail kalkulace
                        <ExternalLink className="ml-2 h-3 w-3" />
                      </Link>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-muted-foreground">
              <Calculator className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-sm">
                Pro tuto zakázku zatím nebyly vytvořeny žádné kalkulace
              </p>
              <Button variant="outline" size="sm" className="mt-4" asChild>
                <Link href="/kalkulace">Vytvořit kalkulaci</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

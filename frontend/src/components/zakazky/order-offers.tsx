"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getOrderOffers } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { OFFER_STATUS_LABELS, type OfferStatus } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { FileText, Calendar, CheckCircle, Clock, XCircle, Send } from "lucide-react";

interface OrderOffersProps {
  orderId: string;
}

export function OrderOffers({ orderId }: OrderOffersProps) {
  const { data: offers, isLoading } = useQuery({
    queryKey: ["offers", "order", orderId],
    queryFn: () => getOrderOffers(orderId),
  });

  const getStatusBadge = (status: OfferStatus) => {
    switch (status) {
      case "draft":
        return { variant: "outline" as const, icon: FileText, color: "" };
      case "sent":
        return { variant: "default" as const, icon: Send, color: "bg-blue-100 text-blue-800" };
      case "accepted":
        return { variant: "default" as const, icon: CheckCircle, color: "bg-green-100 text-green-800" };
      case "rejected":
        return { variant: "destructive" as const, icon: XCircle, color: "" };
      case "expired":
        return { variant: "secondary" as const, icon: Clock, color: "" };
      default:
        return { variant: "outline" as const, icon: FileText, color: "" };
    }
  };

  if (isLoading) {
    return (
      <div>
        <div className="mb-4 flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Nabídky</h2>
        </div>
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
              <p className="mt-2 text-sm text-muted-foreground">Načítání nabídek...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!offers || offers.length === 0) {
    return null;
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <FileText className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-xl font-semibold">Nabídky</h2>
        <span className="text-sm text-muted-foreground">({offers.length})</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {offers.map((offer) => {
          const badge = getStatusBadge(offer.status);
          const Icon = badge.icon;
          const isExpired = new Date(offer.valid_until) < new Date() && offer.status === "draft";
          return (
            <Card key={offer.id} className="hover:bg-accent/50 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg">{offer.number}</CardTitle>
                  <Badge variant={badge.variant} className={badge.color}>
                    <Icon className="h-3 w-3 mr-1" />
                    {OFFER_STATUS_LABELS[offer.status]}
                  </Badge>
                </div>
                <CardDescription>
                  {new Date(offer.created_at).toLocaleDateString("cs-CZ")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Celková cena:</span>
                    <span className="font-semibold text-lg">{formatCurrency(offer.total_price)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">
                      <Calendar className="h-3 w-3 inline mr-1" />
                      Platnost do:
                    </span>
                    <span className={isExpired ? "text-red-600 font-medium" : ""}>
                      {new Date(offer.valid_until).toLocaleDateString("cs-CZ")}
                      {isExpired && " (expirováno)"}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

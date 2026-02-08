"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  CLASSIFICATION_LABELS,
  INBOX_STATUS_LABELS,
  type InboxMessage,
  type InboxClassification,
} from "@/types";
import {
  Mail,
  Clock,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Package,
} from "lucide-react";
import { reclassifyInboxMessage } from "@/lib/api";

interface MessageCardProps {
  message: InboxMessage;
}

const CLASSIFICATION_COLORS: Record<string, string> = {
  poptavka: "bg-blue-100 text-blue-800",
  objednavka: "bg-green-100 text-green-800",
  reklamace: "bg-red-100 text-red-800",
  dotaz: "bg-yellow-100 text-yellow-800",
  faktura: "bg-purple-100 text-purple-800",
  ostatni: "bg-gray-100 text-gray-800",
};

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  classified: "bg-yellow-100 text-yellow-800",
  assigned: "bg-green-100 text-green-800",
  archived: "bg-gray-100 text-gray-800",
};

export function MessageCard({ message }: MessageCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const queryClient = useQueryClient();

  const reclassifyMutation = useMutation({
    mutationFn: async (newClassification: InboxClassification) => {
      return reclassifyInboxMessage(message.id, newClassification);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inbox"] });
    },
  });

  const handleReclassify = async () => {
    if (!message.classification) return;

    // Cycle through classifications for demo
    const classifications: InboxClassification[] = [
      "poptavka",
      "objednavka",
      "reklamace",
      "dotaz",
      "faktura",
      "ostatni",
    ];
    const currentIndex = classifications.indexOf(message.classification);
    const nextClassification =
      classifications[(currentIndex + 1) % classifications.length];

    await reclassifyMutation.mutateAsync(nextClassification);
  };

  return (
    <Card className="cursor-pointer transition-shadow hover:shadow-md">
      <CardContent className="p-4">
        <div
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-start justify-between gap-4"
        >
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <p className="font-medium">
                {message.from_name || message.from_email}
              </p>
              {message.from_name && (
                <span className="text-sm text-muted-foreground">
                  &lt;{message.from_email}&gt;
                </span>
              )}
            </div>

            <p className="font-semibold text-foreground">{message.subject}</p>

            {message.body_text && !isExpanded && (
              <p className="line-clamp-2 text-sm text-muted-foreground">
                {message.body_text}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="secondary"
                className={STATUS_COLORS[message.status]}
              >
                {INBOX_STATUS_LABELS[message.status]}
              </Badge>

              {message.classification && (
                <Badge
                  variant="secondary"
                  className={CLASSIFICATION_COLORS[message.classification]}
                >
                  {CLASSIFICATION_LABELS[message.classification]}
                </Badge>
              )}

              {message.confidence !== null && message.confidence > 0 && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <TrendingUp className="h-3 w-3" />
                  <span>{Math.round(message.confidence * 100)}%</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {new Date(message.received_at).toLocaleDateString("cs-CZ", {
                day: "numeric",
                month: "short",
              })}
            </div>
            <div className="text-xs text-muted-foreground">
              {new Date(message.received_at).toLocaleTimeString("cs-CZ", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </div>

        {message.confidence !== null && message.confidence > 0 && (
          <div className="mt-3">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${message.confidence * 100}%` }}
              />
            </div>
          </div>
        )}

        {isExpanded && (
          <div className="mt-4 space-y-4 border-t pt-4">
            {/* Full email body */}
            {message.body_text && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-foreground">
                  Obsah e-mailu
                </h4>
                <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                  {message.body_text}
                </p>
              </div>
            )}

            {/* Classification details */}
            {message.classification && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-foreground">
                  Klasifikace
                </h4>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="secondary"
                    className={CLASSIFICATION_COLORS[message.classification]}
                  >
                    {CLASSIFICATION_LABELS[message.classification]}
                  </Badge>
                  {message.confidence !== null && message.confidence > 0 && (
                    <span className="text-sm text-muted-foreground">
                      Důvěra: {Math.round(message.confidence * 100)}%
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Received datetime */}
            <div>
              <h4 className="mb-2 text-sm font-semibold text-foreground">
                Přijato
              </h4>
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                {new Date(message.received_at).toLocaleDateString("cs-CZ", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}{" "}
                v{" "}
                {new Date(message.received_at).toLocaleTimeString("cs-CZ", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
            </div>

            {/* Order assignment status */}
            {message.assigned_order_id && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-foreground">
                  Přiřazená zakázka
                </h4>
                <Link
                  href={`/zakazky/${message.assigned_order_id}`}
                  className="flex items-center gap-2 text-sm text-primary hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Package className="h-4 w-4" />
                  Zobrazit zakázku
                </Link>
              </div>
            )}

            {/* Reclassify button */}
            {message.classification && (
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleReclassify();
                  }}
                  disabled={reclassifyMutation.isPending}
                >
                  <RefreshCw
                    className={`mr-2 h-4 w-4 ${
                      reclassifyMutation.isPending ? "animate-spin" : ""
                    }`}
                  />
                  {reclassifyMutation.isPending
                    ? "Reklasifikuji..."
                    : "Reklasifikovat"}
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

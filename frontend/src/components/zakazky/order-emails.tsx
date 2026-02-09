"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getOrderEmails } from "@/lib/api";
import {
  CLASSIFICATION_LABELS,
  type InboxClassification,
  type OrderEmail,
} from "@/types";
import { useQuery } from "@tanstack/react-query";
import { Mail, ArrowDownLeft, ArrowUpRight } from "lucide-react";

interface OrderEmailsProps {
  orderId: string;
}

export function OrderEmails({ orderId }: OrderEmailsProps) {
  const { data: emails, isLoading } = useQuery({
    queryKey: ["emails", "order", orderId],
    queryFn: () => getOrderEmails(orderId),
  });

  if (isLoading) {
    return (
      <div>
        <div className="mb-4 flex items-center gap-2">
          <Mail className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Emailová komunikace</h2>
        </div>
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
              <p className="mt-2 text-sm text-muted-foreground">
                Načítání emailů...
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!emails || emails.length === 0) {
    return null;
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Mail className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-xl font-semibold">Emailová komunikace</h2>
        <span className="text-sm text-muted-foreground">
          ({emails.length})
        </span>
      </div>
      <Card>
        <CardContent className="p-0">
          <div className="divide-y">
            {emails.map((email: OrderEmail) => (
              <EmailTimelineItem key={email.id} email={email} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function EmailTimelineItem({ email }: { email: OrderEmail }) {
  const isOutbound = email.direction === "outbound";
  const DirectionIcon = isOutbound ? ArrowUpRight : ArrowDownLeft;
  const directionColor = isOutbound
    ? "text-blue-600"
    : "text-green-600";
  const directionBg = isOutbound
    ? "bg-blue-50"
    : "bg-green-50";

  return (
    <div className="flex gap-3 px-4 py-3 hover:bg-accent/30 transition-colors">
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${directionBg}`}
      >
        <DirectionIcon className={`h-4 w-4 ${directionColor}`} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium truncate">
            {email.subject}
          </span>
          {email.classification && (
            <Badge variant="secondary" className="text-xs">
              {CLASSIFICATION_LABELS[
                email.classification as InboxClassification
              ] || email.classification}
            </Badge>
          )}
          <Badge
            variant="outline"
            className={`text-xs ${
              isOutbound
                ? "border-blue-200 text-blue-700"
                : "border-green-200 text-green-700"
            }`}
          >
            {isOutbound ? "Odesláno" : "Přijato"}
          </Badge>
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{email.from_email}</span>
          <span>·</span>
          <span>
            {new Date(email.received_at).toLocaleString("cs-CZ", {
              day: "2-digit",
              month: "2-digit",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        {email.body_text && (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
            {email.body_text}
          </p>
        )}
      </div>
    </div>
  );
}

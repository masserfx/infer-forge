"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { getOrderEmails, getDocumentDownloadUrl } from "@/lib/api";
import {
  CLASSIFICATION_LABELS,
  OFFER_STATUS_LABELS,
  type InboxClassification,
  type OfferStatus,
  type OrderEmail,
} from "@/types";
import { useQuery } from "@tanstack/react-query";
import {
  Mail,
  ArrowDownLeft,
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
  FileText,
  Download,
  Printer,
  Eye,
  ExternalLink,
} from "lucide-react";

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
  const [expanded, setExpanded] = useState(false);
  const isOutbound = email.direction === "outbound";
  const DirectionIcon = isOutbound ? ArrowUpRight : ArrowDownLeft;
  const directionColor = isOutbound ? "text-blue-600" : "text-green-600";
  const directionBg = isOutbound ? "bg-blue-50" : "bg-green-50";

  const handlePreview = () => {
    if (email.document_id) {
      const url = getDocumentDownloadUrl(email.document_id);
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };

  const handleDownload = async () => {
    if (email.document_id) {
      const { downloadDocument } = await import("@/lib/api");
      await downloadDocument(
        email.document_id,
        email.document_name || "dokument.pdf",
      );
    }
  };

  const handlePrint = () => {
    if (email.document_id) {
      const url = getDocumentDownloadUrl(email.document_id);
      const printWindow = window.open(url, "_blank");
      if (printWindow) {
        printWindow.addEventListener("load", () => {
          printWindow.print();
        });
      }
    }
  };

  return (
    <div className="transition-colors">
      <button
        type="button"
        className="flex w-full gap-3 px-4 py-3 text-left hover:bg-accent/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
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
            {email.offer_number && (
              <Badge
                variant="secondary"
                className="text-xs bg-purple-100 text-purple-800"
              >
                <FileText className="h-3 w-3 mr-1" />
                {email.offer_number}
                {email.offer_status && (
                  <span className="ml-1 opacity-70">
                    ({OFFER_STATUS_LABELS[email.offer_status as OfferStatus] || email.offer_status})
                  </span>
                )}
              </Badge>
            )}
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <span>{email.from_email}</span>
            <span>&middot;</span>
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
          {!expanded && email.body_text && (
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
              {email.body_text}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center">
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t bg-muted/20 px-4 py-3 ml-11">
          {email.body_text && (
            <pre className="whitespace-pre-wrap text-sm text-foreground/80 font-sans mb-3 max-h-64 overflow-y-auto">
              {email.body_text}
            </pre>
          )}

          {email.document_id && (
            <div className="flex items-center gap-2 pt-2 border-t">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {email.document_name || "Příloha"}
              </span>
              <div className="flex items-center gap-1 ml-auto">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePreview();
                  }}
                >
                  <Eye className="h-3.5 w-3.5 mr-1" />
                  Náhled
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownload();
                  }}
                >
                  <Download className="h-3.5 w-3.5 mr-1" />
                  Stáhnout
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePrint();
                  }}
                >
                  <Printer className="h-3.5 w-3.5 mr-1" />
                  Tisk
                </Button>
              </div>
            </div>
          )}

          {email.offer_id && !email.document_id && (
            <div className="flex items-center gap-2 pt-2 border-t">
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Nabídka {email.offer_number}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

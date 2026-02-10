"use client";

import { useState } from "react";
import { FileText, Loader2, Receipt, Truck, ClipboardList } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getAuthToken } from "@/lib/api";

interface DocumentGeneratorProps {
  orderId: string;
}

type DocType =
  | "offer"
  | "production-sheet"
  | "invoice"
  | "delivery-note"
  | "order-confirmation";

const DOC_FILENAMES: Record<DocType, string> = {
  offer: "nabidka",
  "production-sheet": "pruvodka",
  invoice: "faktura",
  "delivery-note": "dodaci_list",
  "order-confirmation": "objednavka",
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export function DocumentGenerator({ orderId }: DocumentGeneratorProps) {
  const [generating, setGenerating] = useState<DocType | null>(null);

  const generateDocument = async (
    type: DocType,
    body: Record<string, unknown> = {},
  ) => {
    setGenerating(type);

    try {
      const token = getAuthToken();
      const response = await fetch(
        `${API_BASE}/dokumenty/generate/${type}/${orderId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(body),
        },
      );

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || "Chyba při generování dokumentu");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${DOC_FILENAMES[type]}_${orderId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch {
      toast.error("Generování dokumentu se nezdařilo");
    } finally {
      setGenerating(null);
    }
  };

  const isDisabled = generating !== null;

  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="h-5 w-5 text-muted-foreground" />
        <h3 className="font-semibold">Generování dokumentů</h3>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => generateDocument("offer")}
          disabled={isDisabled}
        >
          {generating === "offer" ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FileText className="mr-2 h-4 w-4" />
          )}
          Cenová nabídka
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => generateDocument("production-sheet")}
          disabled={isDisabled}
        >
          {generating === "production-sheet" ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <ClipboardList className="mr-2 h-4 w-4" />
          )}
          Výrobní průvodka
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" disabled={isDisabled}>
              {generating === "invoice" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Receipt className="mr-2 h-4 w-4" />
              )}
              Faktura
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem
              onClick={() =>
                generateDocument("invoice", { invoice_type: "final" })
              }
            >
              Konečná faktura
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() =>
                generateDocument("invoice", { invoice_type: "advance" })
              }
            >
              Zálohová faktura
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() =>
                generateDocument("invoice", { invoice_type: "proforma" })
              }
            >
              Proforma faktura
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="outline"
          size="sm"
          onClick={() => generateDocument("delivery-note")}
          disabled={isDisabled}
        >
          {generating === "delivery-note" ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Truck className="mr-2 h-4 w-4" />
          )}
          Dodací list
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => generateDocument("order-confirmation")}
          disabled={isDisabled}
        >
          {generating === "order-confirmation" ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FileText className="mr-2 h-4 w-4" />
          )}
          Potvrzení objednávky
        </Button>
      </div>
    </div>
  );
}

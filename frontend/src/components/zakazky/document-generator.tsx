"use client";

import { useState } from "react";
import { FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getAuthToken } from "@/lib/api";

interface DocumentGeneratorProps {
  orderId: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export function DocumentGenerator({ orderId }: DocumentGeneratorProps) {
  const [generatingOffer, setGeneratingOffer] = useState(false);
  const [generatingSheet, setGeneratingSheet] = useState(false);

  const generateDocument = async (type: "offer" | "production-sheet") => {
    const setter = type === "offer" ? setGeneratingOffer : setGeneratingSheet;
    setter(true);

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
          body: JSON.stringify({}),
        },
      );

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || "Chyba při generování dokumentu");
      }

      // Download the PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        type === "offer"
          ? `nabidka_${orderId}.pdf`
          : `pruvodka_${orderId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      console.error("Document generation failed:", error);
    } finally {
      setter(false);
    }
  };

  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="h-5 w-5 text-muted-foreground" />
        <h3 className="font-semibold">Generování dokumentů</h3>
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => generateDocument("offer")}
          disabled={generatingOffer}
        >
          {generatingOffer ? (
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
          disabled={generatingSheet}
        >
          {generatingSheet ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FileText className="mr-2 h-4 w-4" />
          )}
          Výrobní průvodka
        </Button>
      </div>
    </div>
  );
}

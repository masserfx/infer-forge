"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <div className="mx-auto max-w-md space-y-6 text-center">
        <AlertTriangle className="mx-auto h-12 w-12 text-destructive" />
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">
            Nastala chyba
          </h2>
          <p className="text-sm text-muted-foreground">
            Při načítání stránky došlo k neočekávané chybě. Zkuste to prosím znovu
            nebo se vraťte na dashboard.
          </p>
        </div>
        <div className="flex justify-center gap-3">
          <Button onClick={reset} variant="default">
            Zkusit znovu
          </Button>
          <Button variant="outline" asChild>
            <a href="/dashboard">Dashboard</a>
          </Button>
        </div>
      </div>
    </div>
  );
}

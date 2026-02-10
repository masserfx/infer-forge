"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="mx-auto max-w-md space-y-6 text-center">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">
            Nastala chyba
          </h1>
          <p className="text-muted-foreground">
            Omlouváme se, něco se pokazilo. Zkuste to prosím znovu.
          </p>
        </div>
        <Button onClick={reset} size="lg">
          Zkusit znovu
        </Button>
      </div>
    </div>
  );
}

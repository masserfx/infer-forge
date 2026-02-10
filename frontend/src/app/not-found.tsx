import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="mx-auto max-w-md space-y-6 text-center">
        <div className="space-y-2">
          <h1 className="text-6xl font-bold tracking-tight">404</h1>
          <h2 className="text-2xl font-semibold">Stránka nenalezena</h2>
          <p className="text-muted-foreground">
            Požadovaná stránka neexistuje nebo byla přesunuta.
          </p>
        </div>
        <Button asChild size="lg">
          <Link href="/dashboard">Zpět na dashboard</Link>
        </Button>
      </div>
    </div>
  );
}

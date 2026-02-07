"use client";

import { useAuth } from "@/lib/auth-provider";
import { Badge } from "@/components/ui/badge";
import { User, Shield, Mail, Phone, Server, Database } from "lucide-react";

const ROLE_LABELS: Record<string, string> = {
  admin: "Administrátor",
  obchodnik: "Obchodník",
  technolog: "Technolog",
  vedeni: "Vedení",
  ucetni: "Účetní",
};

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-red-100 text-red-800",
  obchodnik: "bg-blue-100 text-blue-800",
  technolog: "bg-orange-100 text-orange-800",
  vedeni: "bg-purple-100 text-purple-800",
  ucetni: "bg-green-100 text-green-800",
};

export default function NastaveniPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Nastavení</h1>
        <p className="text-muted-foreground">Konfigurace aplikace a profil</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* User Profile */}
        <div className="rounded-lg border bg-card">
          <div className="border-b p-4">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <User className="h-5 w-5" />
              Profil uživatele
            </h2>
          </div>
          <div className="space-y-4 p-4">
            {user ? (
              <>
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <User className="h-8 w-8" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold">{user.full_name}</p>
                    <Badge
                      variant="secondary"
                      className={ROLE_COLORS[user.role] || ""}
                    >
                      {ROLE_LABELS[user.role] || user.role}
                    </Badge>
                  </div>
                </div>
                <div className="space-y-3 pt-2">
                  <div className="flex items-center gap-3 text-sm">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    <span>{user.email}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <span>{user.phone || "Neuvedeno"}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <span>
                      Stav:{" "}
                      <Badge
                        variant="secondary"
                        className={
                          user.is_active
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }
                      >
                        {user.is_active ? "Aktivní" : "Neaktivní"}
                      </Badge>
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Nepodařilo se načíst profil
              </p>
            )}
          </div>
        </div>

        {/* System Info */}
        <div className="rounded-lg border bg-card">
          <div className="border-b p-4">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Server className="h-5 w-5" />
              Systémové informace
            </h2>
          </div>
          <div className="space-y-3 p-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Aplikace</span>
              <span className="font-medium">INFER FORGE</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Verze</span>
              <Badge variant="outline">0.1.0</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Firma</span>
              <span className="font-medium">Infer s.r.o.</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">IČO</span>
              <span className="font-mono">04856562</span>
            </div>
          </div>
        </div>

        {/* Integrations */}
        <div className="rounded-lg border bg-card">
          <div className="border-b p-4">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Database className="h-5 w-5" />
              Integrace
            </h2>
          </div>
          <div className="space-y-3 p-4">
            <div className="flex items-center justify-between text-sm">
              <span>Pohoda XML API</span>
              <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                Konfigurace
              </Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>E-mail (IMAP/SMTP)</span>
              <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                Konfigurace
              </Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>AI klasifikace</span>
              <Badge variant="secondary" className="bg-green-100 text-green-800">
                Aktivní
              </Badge>
            </div>
          </div>
        </div>

        {/* Permissions */}
        <div className="rounded-lg border bg-card">
          <div className="border-b p-4">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Shield className="h-5 w-5" />
              Oprávnění
            </h2>
          </div>
          <div className="space-y-3 p-4">
            <div className="space-y-2 text-sm">
              {user?.role === "admin" && (
                <p className="text-muted-foreground">
                  Plný přístup ke všem funkcím systému.
                </p>
              )}
              {user?.role === "obchodnik" && (
                <p className="text-muted-foreground">
                  Správa zakázek, zákazníků, kalkulací a nabídek.
                </p>
              )}
              {user?.role === "technolog" && (
                <p className="text-muted-foreground">
                  Správa zakázek, kalkulací a výrobní dokumentace.
                </p>
              )}
              {user?.role === "vedeni" && (
                <p className="text-muted-foreground">
                  Plný přístup, reporting a schvalování.
                </p>
              )}
              {user?.role === "ucetni" && (
                <p className="text-muted-foreground">
                  Fakturace, reporting a Pohoda synchronizace.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

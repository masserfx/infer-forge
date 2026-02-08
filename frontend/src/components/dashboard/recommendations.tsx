"use client";

import { useQuery } from "@tanstack/react-query";
import { getRecommendations } from "@/lib/api";
import { AlertTriangle, AlertCircle, Info, ArrowRight } from "lucide-react";
import Link from "next/link";

const severityConfig = {
  critical: {
    icon: AlertTriangle,
    bg: "bg-red-50 border-red-200",
    iconColor: "text-red-600",
    textColor: "text-red-900",
  },
  warning: {
    icon: AlertCircle,
    bg: "bg-yellow-50 border-yellow-200",
    iconColor: "text-yellow-600",
    textColor: "text-yellow-900",
  },
  info: {
    icon: Info,
    bg: "bg-blue-50 border-blue-200",
    iconColor: "text-blue-600",
    textColor: "text-blue-900",
  },
};

export function Recommendations() {
  const { data: recommendations = [], isLoading } = useQuery({
    queryKey: ["recommendations"],
    queryFn: () => getRecommendations(5),
    refetchInterval: 60000,
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border bg-card">
        <div className="border-b p-4">
          <h2 className="text-lg font-semibold">Doporučené akce</h2>
        </div>
        <div className="p-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (recommendations.length === 0) {
    return (
      <div className="rounded-lg border bg-card">
        <div className="border-b p-4">
          <h2 className="text-lg font-semibold">Doporučené akce</h2>
        </div>
        <div className="p-8 text-center">
          <div className="mx-auto h-12 w-12 rounded-full bg-green-100 flex items-center justify-center mb-3">
            <Info className="h-6 w-6 text-green-600" />
          </div>
          <p className="text-sm font-medium text-green-800">Vše v pořádku</p>
          <p className="text-xs text-muted-foreground mt-1">
            Žádné urgentní akce k vyřízení
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b p-4">
        <h2 className="text-lg font-semibold">Doporučené akce</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Na základě analýzy stavu systému
        </p>
      </div>
      <div className="p-4 space-y-2">
        {recommendations.map((rec, idx) => {
          const config = severityConfig[rec.severity] || severityConfig.info;
          const Icon = config.icon;
          return (
            <Link
              key={idx}
              href={rec.action_url}
              className={`flex items-center gap-3 rounded-lg border p-3 transition-colors hover:opacity-80 ${config.bg}`}
            >
              <Icon className={`h-5 w-5 shrink-0 ${config.iconColor}`} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${config.textColor}`}>
                  {rec.title}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {rec.description}
                </p>
              </div>
              <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            </Link>
          );
        })}
      </div>
    </div>
  );
}

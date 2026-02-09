"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface StageStat {
  stage: string;
  total: number;
  success: number;
  failed: number;
  avg_time_ms: number;
  total_tokens: number;
}

interface PipelineFunnelProps {
  stages: StageStat[];
}

const stageLabels: Record<string, string> = {
  ingest: "Příjem",
  classify: "Klasifikace",
  parse: "Parsování",
  ocr: "OCR",
  analyze: "Analýza",
  orchestrate: "Orchestrace",
  calculate: "Kalkulace",
  offer: "Nabídka",
};

const stageOrder = ["ingest", "classify", "parse", "orchestrate", "calculate", "offer"];

export function PipelineFunnel({ stages }: PipelineFunnelProps) {
  if (!stages || stages.length === 0) {
    return null;
  }

  // Sort stages by pipeline order
  const sorted = stageOrder
    .map((s) => stages.find((st) => st.stage === s))
    .filter((s): s is StageStat => !!s);

  // Fallback: include any stages not in stageOrder
  const remaining = stages.filter((s) => !stageOrder.includes(s.stage));
  const all = [...sorted, ...remaining];

  const maxTotal = Math.max(...all.map((s) => s.total), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Pipeline Funnel</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {all.map((stage, i) => {
            const widthPercent = Math.max((stage.total / maxTotal) * 100, 8);
            const successRate = stage.total > 0
              ? Math.round((stage.success / stage.total) * 100)
              : 0;

            return (
              <div key={stage.stage}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-bold">
                      {i + 1}
                    </span>
                    <span className="text-sm font-medium">
                      {stageLabels[stage.stage] ?? stage.stage}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{stage.total} celkem</span>
                    <Badge variant="default" className="text-xs">{stage.success} OK</Badge>
                    {stage.failed > 0 && (
                      <Badge variant="destructive" className="text-xs">{stage.failed} chyb</Badge>
                    )}
                    <span>{Math.round(stage.avg_time_ms)} ms</span>
                  </div>
                </div>

                <div className="relative h-6 w-full rounded bg-muted overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 rounded bg-gradient-to-r from-teal-500 to-teal-400 transition-all"
                    style={{ width: `${widthPercent}%` }}
                  />
                  <div
                    className="absolute inset-y-0 left-0 flex items-center px-2"
                  >
                    <span className="text-xs font-medium text-white drop-shadow">
                      {successRate}% úspěšnost
                    </span>
                  </div>
                </div>

                {i < all.length - 1 && (
                  <div className="flex justify-center py-1">
                    <div className="h-3 w-px bg-border" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

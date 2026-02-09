"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface MethodBucket {
  method: string;
  count: number;
  avg_confidence: number;
  avg_time_ms: number;
}

interface AgentComparisonProps {
  methods: MethodBucket[];
  tokensByStage: Record<string, number>;
}

const methodLabels: Record<string, string> = {
  heuristic: "Heuristika",
  ai_claude: "Claude AI",
  default_fallback: "Fallback",
  unknown: "Neznámá",
};

export function AgentComparison({ methods, tokensByStage }: AgentComparisonProps) {
  if (!methods || methods.length === 0) {
    return null;
  }

  const maxCount = Math.max(...methods.map((m) => m.count), 1);
  const classifyTokens = tokensByStage?.classify ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Porovnání metod klasifikace</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2">
          {methods.map((m) => (
            <div
              key={m.method}
              className="rounded-lg border p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">
                  {methodLabels[m.method] ?? m.method}
                </h3>
                <Badge variant="secondary">{m.count}x</Badge>
              </div>

              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="font-medium">{Math.round(m.avg_confidence * 100)}%</span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-muted">
                    <div
                      className="h-2 rounded-full bg-green-500 transition-all"
                      style={{ width: `${Math.round(m.avg_confidence * 100)}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Podíl</span>
                    <span className="font-medium">{Math.round((m.count / maxCount) * 100)}%</span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-muted">
                    <div
                      className="h-2 rounded-full bg-blue-500 transition-all"
                      style={{ width: `${Math.round((m.count / maxCount) * 100)}%` }}
                    />
                  </div>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Avg čas</span>
                  <span className="font-medium">{Math.round(m.avg_time_ms)} ms</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {classifyTokens > 0 && (
          <p className="mt-3 text-xs text-muted-foreground">
            Celkem tokenů na klasifikaci: {classifyTokens.toLocaleString("cs-CZ")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

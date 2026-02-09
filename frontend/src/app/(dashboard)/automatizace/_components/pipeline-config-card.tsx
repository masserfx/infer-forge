"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Settings } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface PipelineConfig {
  auto_calculate: boolean;
  auto_offer: boolean;
  auto_create_orders: boolean;
  review_threshold: number;
}

async function fetchConfig(): Promise<PipelineConfig> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/orchestrace/config`, { headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function updateConfig(data: Partial<PipelineConfig>): Promise<PipelineConfig> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/orchestrace/config`, {
    method: "PUT",
    headers,
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function PipelineConfigCard() {
  const queryClient = useQueryClient();

  const { data: config } = useQuery<PipelineConfig>({
    queryKey: ["pipeline-config"],
    queryFn: fetchConfig,
  });

  const mutation = useMutation({
    mutationFn: updateConfig,
    onSuccess: (data) => {
      queryClient.setQueryData(["pipeline-config"], data);
    },
  });

  if (!config) return null;

  const toggle = (key: keyof PipelineConfig, value: boolean) => {
    mutation.mutate({ [key]: value });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Konfigurace pipeline
        </CardTitle>
        <CardDescription>Nastavení automatického zpracování</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <Label htmlFor="auto-orders" className="flex-1">
            <div className="font-medium">Auto-vytváření zakázek</div>
            <div className="text-sm text-muted-foreground">Automaticky vytvořit zakázku z parsovaného emailu</div>
          </Label>
          <Switch
            id="auto-orders"
            checked={config.auto_create_orders}
            onCheckedChange={(v) => toggle("auto_create_orders", v)}
          />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="auto-calc" className="flex-1">
            <div className="font-medium">Auto-kalkulace</div>
            <div className="text-sm text-muted-foreground">Spustit AI kalkulaci pro poptávky</div>
          </Label>
          <Switch
            id="auto-calc"
            checked={config.auto_calculate}
            onCheckedChange={(v) => toggle("auto_calculate", v)}
          />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="auto-offer" className="flex-1">
            <div className="font-medium">Auto-nabídka</div>
            <div className="text-sm text-muted-foreground">Generovat nabídku po schválení kalkulace</div>
          </Label>
          <Switch
            id="auto-offer"
            checked={config.auto_offer}
            onCheckedChange={(v) => toggle("auto_offer", v)}
          />
        </div>

        <div className="space-y-3">
          <Label>
            <div className="font-medium">Práh pro manuální review</div>
            <div className="text-sm text-muted-foreground">
              Klasifikace s confidence pod tímto prahem vyžaduje ruční kontrolu
            </div>
          </Label>
          <div className="flex items-center gap-4">
            <Slider
              value={[config.review_threshold * 100]}
              min={0}
              max={100}
              step={5}
              onValueCommit={(v) => mutation.mutate({ review_threshold: v[0] / 100 })}
              className="flex-1"
            />
            <span className="text-sm font-mono w-12 text-right">
              {Math.round(config.review_threshold * 100)}%
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

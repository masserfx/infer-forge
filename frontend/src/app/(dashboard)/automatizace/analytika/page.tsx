"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, Brain, Mail, Percent, TrendingUp, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatsPeriodSelector } from "../_components/stats-period-selector";
import { ClassificationOverview } from "../_components/classification-overview";
import { EntityExtractionRates } from "../_components/entity-extraction-rates";
import { ConfidenceDistribution } from "../_components/confidence-distribution";
import { AgentComparison } from "../_components/agent-comparison";
import { PipelineFunnel } from "../_components/pipeline-funnel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface NLPAnalytics {
  period: string;
  total_emails: number;
  classification_distribution: {
    category: string;
    count: number;
    avg_confidence: number;
  }[];
  classification_methods: {
    method: string;
    count: number;
    avg_confidence: number;
    avg_time_ms: number;
  }[];
  escalation_rate: number;
  avg_confidence: number;
  confidence_buckets: { range: string; count: number }[];
  entity_extraction: {
    field: string;
    extracted_count: number;
    total_count: number;
    rate: number;
  }[];
  stage_success_rates: {
    stage: string;
    total: number;
    success: number;
    failed: number;
    avg_time_ms: number;
    total_tokens: number;
  }[];
  total_tokens: number;
  tokens_by_stage: Record<string, number>;
  confidence_trend: {
    date: string;
    avg_confidence: number;
    email_count: number;
  }[];
  top_materials: { value: string; count: number }[];
  top_companies: { value: string; count: number }[];
}

async function fetchAnalytics(period: string): Promise<NLPAnalytics> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(
    `${API_BASE}/orchestrace/nlp-analytics?period=${period}`,
    { headers }
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function AnalytikaPage() {
  const [period, setPeriod] = useState("all");

  const { data, isLoading } = useQuery<NLPAnalytics>({
    queryKey: ["nlp-analytics", period],
    queryFn: () => fetchAnalytics(period),
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/automatizace">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Zpět
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">NLP Analytika</h1>
            <p className="text-muted-foreground">
              Detailní analýza zpracování emailů a AI klasifikace
            </p>
          </div>
        </div>
        <StatsPeriodSelector value={period} onChange={setPeriod} />
      </div>

      {isLoading && (
        <p className="text-muted-foreground">Načítání analytiky...</p>
      )}

      {data && (
        <>
          {/* KPI Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Celkem emailů</CardTitle>
                <Mail className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {data.total_emails.toLocaleString("cs-CZ")}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg confidence</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {Math.round(data.avg_confidence * 100)}%
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Escalation rate</CardTitle>
                <Percent className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {Math.round(data.escalation_rate * 100)}%
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Celkem tokenů</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {data.total_tokens.toLocaleString("cs-CZ")}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Row 2: Classification + Entity extraction */}
          <div className="grid gap-6 lg:grid-cols-2">
            <ClassificationOverview data={data.classification_distribution} />
            <EntityExtractionRates data={data.entity_extraction} />
          </div>

          {/* Row 3: Confidence Distribution */}
          <ConfidenceDistribution
            buckets={data.confidence_buckets}
            trend={data.confidence_trend}
          />

          {/* Row 4: Agent Comparison + Pipeline Funnel */}
          <div className="grid gap-6 lg:grid-cols-2">
            <AgentComparison
              methods={data.classification_methods}
              tokensByStage={data.tokens_by_stage}
            />
            <PipelineFunnel stages={data.stage_success_rates} />
          </div>

          {/* Row 5: Top companies & materials */}
          {(data.top_companies.length > 0 || data.top_materials.length > 0) && (
            <div className="grid gap-6 lg:grid-cols-2">
              {data.top_companies.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Brain className="h-4 w-4" />
                      Top rozpoznané firmy
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {data.top_companies.map((c, i) => (
                        <div key={i} className="flex items-center justify-between rounded border p-2">
                          <span className="text-sm">{c.value}</span>
                          <span className="text-sm font-medium text-muted-foreground">{c.count}x</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {data.top_materials.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Brain className="h-4 w-4" />
                      Top rozpoznané materiály
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {data.top_materials.map((m, i) => (
                        <div key={i} className="flex items-center justify-between rounded border p-2">
                          <span className="text-sm">{m.value}</span>
                          <span className="text-sm font-medium text-muted-foreground">{m.count}x</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

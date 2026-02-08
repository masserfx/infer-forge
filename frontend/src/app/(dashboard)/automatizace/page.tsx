"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, Clock, Cpu, RefreshCw, CheckCircle, XCircle, Zap, BarChart3, Send, Mail } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// API client
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }

  return res.json() as Promise<T>;
}

// Types
interface PipelineStats {
  total_tasks: number;
  by_stage: Record<string, number>;
  by_status: Record<string, number>;
  total_tokens_used: number;
  avg_processing_time_ms: number;
  error_rate: number;
  dlq_unresolved: number;
}

interface ProcessingTask {
  id: string;
  inbox_message_id: string | null;
  celery_task_id: string | null;
  stage: string;
  status: string;
  tokens_used: number | null;
  processing_time_ms: number | null;
  retry_count: number;
  error_message: string | null;
  created_at: string;
}

interface DLQEntry {
  id: string;
  original_task: string;
  stage: string;
  error_message: string | null;
  retry_count: number;
  resolved: boolean;
  resolved_at: string | null;
  created_at: string;
}

interface DLQListResponse {
  items: DLQEntry[];
  total: number;
  unresolved: number;
}

// Stage and status label maps (Czech)
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

const statusVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "outline",
  running: "secondary",
  success: "default",
  failed: "destructive",
  dlq: "destructive",
};

interface TestEmailResult {
  pipeline_stages: {
    stage: string;
    status: string;
    time_ms?: number;
    category?: string;
    confidence?: number;
    method?: string;
    inbox_message_id?: string;
    customer_id?: string;
    order_id?: string;
    customer_created?: boolean;
    order_created?: boolean;
    error?: string;
  }[];
  inbox_message_id?: string;
  classification?: string;
  classification_confidence?: number;
  classification_method?: string;
  customer_id?: string;
  order_id?: string;
  total_time_ms: number;
  errors: string[];
}

export default function AutomatizacePage() {
  const queryClient = useQueryClient();
  const [testEmail, setTestEmail] = useState({ from_email: "", subject: "", body_text: "" });
  const [testResult, setTestResult] = useState<TestEmailResult | null>(null);

  const testEmailMutation = useMutation({
    mutationFn: (data: { from_email: string; subject: string; body_text: string }) =>
      fetchApi<TestEmailResult>("/orchestrace/test-email", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: (data) => {
      setTestResult(data);
      queryClient.invalidateQueries({ queryKey: ["orchestration-stats"] });
      queryClient.invalidateQueries({ queryKey: ["orchestration-tasks"] });
    },
  });

  const { data: stats } = useQuery<PipelineStats>({
    queryKey: ["orchestration-stats"],
    queryFn: () => fetchApi<PipelineStats>("/orchestrace/stats"),
    refetchInterval: 10000,
  });

  const { data: tasks, isLoading: tasksLoading } = useQuery<ProcessingTask[]>({
    queryKey: ["orchestration-tasks"],
    queryFn: () => fetchApi<ProcessingTask[]>("/orchestrace/tasks?limit=20"),
    refetchInterval: 10000,
  });

  const { data: dlqData, isLoading: dlqLoading } = useQuery<DLQListResponse>({
    queryKey: ["orchestration-dlq"],
    queryFn: () => fetchApi<DLQListResponse>("/orchestrace/dlq?resolved=false"),
    refetchInterval: 15000,
  });

  const resolveMutation = useMutation({
    mutationFn: (entryId: string) =>
      fetchApi(`/orchestrace/dlq/${entryId}/resolve`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orchestration-dlq"] }),
  });

  const retryMutation = useMutation({
    mutationFn: (entryId: string) =>
      fetchApi(`/orchestrace/dlq/${entryId}/retry`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orchestration-dlq"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Automatizace</h1>
          <p className="text-muted-foreground">Pipeline pro automatické zpracování dokumentů</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => {
          queryClient.invalidateQueries({ queryKey: ["orchestration-stats"] });
          queryClient.invalidateQueries({ queryKey: ["orchestration-tasks"] });
          queryClient.invalidateQueries({ queryKey: ["orchestration-dlq"] });
        }}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Obnovit
        </Button>
      </div>

      {/* Test Email */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Test email pipeline
          </CardTitle>
          <CardDescription>
            Odešlete testovací email a sledujte průběh celého pipeline
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="test-from">Od (email)</Label>
              <Input
                id="test-from"
                placeholder="novak@firma.cz"
                value={testEmail.from_email}
                onChange={(e) => setTestEmail((prev) => ({ ...prev, from_email: e.target.value }))}
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="test-subject">Předmět</Label>
              <Input
                id="test-subject"
                placeholder="Poptávka na výrobu přírub DN200"
                value={testEmail.subject}
                onChange={(e) => setTestEmail((prev) => ({ ...prev, subject: e.target.value }))}
              />
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <Label htmlFor="test-body">Text emailu</Label>
            <Textarea
              id="test-body"
              placeholder="Dobrý den, potřebujeme nacenit výrobu..."
              rows={4}
              value={testEmail.body_text}
              onChange={(e) => setTestEmail((prev) => ({ ...prev, body_text: e.target.value }))}
            />
          </div>
          <div className="mt-4 flex items-center gap-4">
            <Button
              onClick={() => testEmailMutation.mutate(testEmail)}
              disabled={testEmailMutation.isPending || !testEmail.from_email || !testEmail.subject || !testEmail.body_text}
            >
              {testEmailMutation.isPending ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Zpracovávám...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Odeslat test
                </>
              )}
            </Button>
            {testEmailMutation.isError && (
              <p className="text-sm text-destructive">
                Chyba: {(testEmailMutation.error as Error).message}
              </p>
            )}
          </div>

          {/* Test Result */}
          {testResult && (
            <div className="mt-6 space-y-4 rounded-lg border bg-muted/30 p-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Výsledek pipeline</h3>
                <Badge variant={testResult.errors.length > 0 ? "destructive" : "default"}>
                  {testResult.total_time_ms}ms
                </Badge>
              </div>

              <div className="space-y-2">
                {testResult.pipeline_stages.map((stage, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 rounded border bg-background p-3"
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-bold">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{stageLabels[stage.stage] ?? stage.stage}</span>
                        <Badge variant={stage.status === "success" ? "default" : "destructive"}>
                          {stage.status}
                        </Badge>
                        {stage.time_ms !== undefined && (
                          <span className="text-xs text-muted-foreground">{stage.time_ms}ms</span>
                        )}
                      </div>
                      {stage.category && (
                        <p className="text-sm text-muted-foreground">
                          Kategorie: <span className="font-medium text-foreground">{stage.category}</span>
                          {stage.confidence !== undefined && ` (${Math.round(stage.confidence * 100)}%)`}
                          {stage.method && ` — metoda: ${stage.method}`}
                        </p>
                      )}
                      {stage.order_created && (
                        <p className="text-sm text-green-600">
                          Zakázka vytvořena
                          {stage.customer_created && " + nový zákazník"}
                        </p>
                      )}
                      {stage.error && (
                        <p className="text-sm text-destructive">{stage.error}</p>
                      )}
                    </div>
                    {stage.status === "success" ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-destructive" />
                    )}
                  </div>
                ))}
              </div>

              {testResult.errors.length > 0 && (
                <div className="rounded border border-destructive/50 bg-destructive/10 p-3">
                  <p className="text-sm font-medium text-destructive">Chyby:</p>
                  {testResult.errors.map((err, i) => (
                    <p key={i} className="text-sm text-destructive">{err}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Celkem úloh</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_tasks ?? 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Chybovost</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats ? `${(stats.error_rate * 100).toFixed(1)}%` : "0%"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tokeny celkem</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.total_tokens_used?.toLocaleString("cs-CZ") ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Prům. čas</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats ? `${Math.round(stats.avg_processing_time_ms)}ms` : "0ms"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">DLQ nevyřešeno</CardTitle>
            <XCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {stats?.dlq_unresolved ?? 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stage breakdown */}
      {stats && Object.keys(stats.by_stage).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Rozložení podle fází
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Object.entries(stats.by_stage).map(([stage, count]) => (
                <div key={stage} className="flex items-center gap-2 rounded-lg border p-3">
                  <span className="text-sm font-medium">{stageLabels[stage] ?? stage}</span>
                  <Badge variant="secondary">{count}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Processing Tasks Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            Poslední zpracované úlohy
          </CardTitle>
        </CardHeader>
        <CardContent>
          {tasksLoading ? (
            <p className="text-muted-foreground">Načítání...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fáze</TableHead>
                  <TableHead>Stav</TableHead>
                  <TableHead>Tokeny</TableHead>
                  <TableHead>Čas (ms)</TableHead>
                  <TableHead>Opakování</TableHead>
                  <TableHead>Vytvořeno</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(tasks ?? []).map((task) => (
                  <TableRow key={task.id}>
                    <TableCell>
                      <Badge variant="outline">{stageLabels[task.stage] ?? task.stage}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariants[task.status] ?? "outline"}>
                        {task.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{task.tokens_used ?? "-"}</TableCell>
                    <TableCell>{task.processing_time_ms ?? "-"}</TableCell>
                    <TableCell>{task.retry_count}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(task.created_at).toLocaleString("cs-CZ")}
                    </TableCell>
                  </TableRow>
                ))}
                {(tasks ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      Žádné úlohy
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Dead Letter Queue */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Dead Letter Queue
            {dlqData && dlqData.unresolved > 0 && (
              <Badge variant="destructive">{dlqData.unresolved}</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {dlqLoading ? (
            <p className="text-muted-foreground">Načítání...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Úloha</TableHead>
                  <TableHead>Fáze</TableHead>
                  <TableHead>Chyba</TableHead>
                  <TableHead>Opakování</TableHead>
                  <TableHead>Vytvořeno</TableHead>
                  <TableHead>Akce</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(dlqData?.items ?? []).map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="font-mono text-xs">{entry.original_task.split(".").pop()}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{stageLabels[entry.stage] ?? entry.stage}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate text-sm" title={entry.error_message ?? ""}>
                      {entry.error_message ?? "-"}
                    </TableCell>
                    <TableCell>{entry.retry_count}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(entry.created_at).toLocaleString("cs-CZ")}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => retryMutation.mutate(entry.id)}
                          disabled={retryMutation.isPending}
                        >
                          <RefreshCw className="mr-1 h-3 w-3" />
                          Retry
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => resolveMutation.mutate(entry.id)}
                          disabled={resolveMutation.isPending}
                        >
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Vyřešit
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {(dlqData?.items ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      Žádné nevyřešené záznamy v DLQ
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

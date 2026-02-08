"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, Clock, Cpu, RefreshCw, CheckCircle, XCircle, Zap, BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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

export default function AutomatizacePage() {
  const queryClient = useQueryClient();

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

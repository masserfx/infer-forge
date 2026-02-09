"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, Mail } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface TaskDetail {
  id: string;
  inbox_message_id: string | null;
  celery_task_id: string | null;
  stage: string;
  status: string;
  tokens_used: number | null;
  processing_time_ms: number | null;
  retry_count: number;
  error_message: string | null;
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  order_id: string | null;
  error_traceback: string | null;
  created_at: string;
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

const statusVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "outline",
  running: "secondary",
  success: "default",
  failed: "destructive",
  dlq: "destructive",
};

async function fetchTaskDetail(taskId: string): Promise<TaskDetail> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/orchestrace/tasks/${taskId}`, { headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

interface TaskDetailSheetProps {
  taskId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TaskDetailSheet({ taskId, open, onOpenChange }: TaskDetailSheetProps) {
  const { data: task, isLoading } = useQuery<TaskDetail>({
    queryKey: ["task-detail", taskId],
    queryFn: () => fetchTaskDetail(taskId!),
    enabled: !!taskId && open,
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[500px] sm:max-w-[500px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Detail úlohy</SheetTitle>
        </SheetHeader>

        {isLoading && <p className="mt-4 text-muted-foreground">Načítání...</p>}

        {task && (
          <div className="mt-4 space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{stageLabels[task.stage] ?? task.stage}</Badge>
              <Badge variant={statusVariants[task.status] ?? "outline"}>{task.status}</Badge>
              {task.processing_time_ms && (
                <span className="text-sm text-muted-foreground">{task.processing_time_ms}ms</span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm">
              <span className="text-muted-foreground">Tokeny:</span>
              <span>{task.tokens_used ?? "-"}</span>
              <span className="text-muted-foreground">Opakování:</span>
              <span>{task.retry_count}</span>
              <span className="text-muted-foreground">Vytvořeno:</span>
              <span>{new Date(task.created_at).toLocaleString("cs-CZ")}</span>
            </div>

            {/* Links */}
            <div className="flex gap-2">
              {task.order_id && (
                <Button variant="outline" size="sm" asChild>
                  <a href={`/zakazky/${task.order_id}`}>
                    <FileText className="mr-1 h-3 w-3" />
                    Zakázka
                  </a>
                </Button>
              )}
              {task.inbox_message_id && (
                <Button variant="outline" size="sm" asChild>
                  <a href={`/inbox?id=${task.inbox_message_id}`}>
                    <Mail className="mr-1 h-3 w-3" />
                    Inbox
                  </a>
                </Button>
              )}
            </div>

            {/* Error */}
            {task.error_message && (
              <div className="rounded border border-destructive/50 bg-destructive/10 p-3">
                <p className="text-sm font-medium text-destructive">Chyba</p>
                <p className="text-sm text-destructive">{task.error_message}</p>
              </div>
            )}

            {/* Error Traceback */}
            {task.error_traceback && (
              <div>
                <p className="text-sm font-medium mb-1">Traceback</p>
                <pre className="rounded bg-muted p-3 text-xs overflow-auto max-h-48">
                  {task.error_traceback}
                </pre>
              </div>
            )}

            {/* Input Data */}
            {task.input_data && Object.keys(task.input_data).length > 0 && (
              <div>
                <p className="text-sm font-medium mb-1">Vstupní data</p>
                <pre className="rounded bg-muted p-3 text-xs overflow-auto max-h-48">
                  {JSON.stringify(task.input_data, null, 2)}
                </pre>
              </div>
            )}

            {/* Output Data */}
            {task.output_data && Object.keys(task.output_data).length > 0 && (
              <div>
                <p className="text-sm font-medium mb-1">Výstupní data</p>
                <pre className="rounded bg-muted p-3 text-xs overflow-auto max-h-48">
                  {JSON.stringify(task.output_data, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

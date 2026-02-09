"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, XCircle, ClipboardCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface PendingApproval {
  id: string;
  order_id: string;
  order_number: string;
  customer_name: string | null;
  name: string;
  total_price: number;
  note: string | null;
  created_at: string;
}

async function fetchPendingApprovals(): Promise<PendingApproval[]> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/orchestrace/pending-approvals`, { headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function approveCalc(calcId: string): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/orchestrace/approve-calculation/${calcId}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) throw new Error(await res.text());
}

async function rejectCalc(calcId: string, reason?: string): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/orchestrace/reject-calculation/${calcId}`, {
    method: "POST",
    headers,
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error(await res.text());
}

export function PendingApprovals() {
  const queryClient = useQueryClient();

  const { data: approvals } = useQuery<PendingApproval[]>({
    queryKey: ["pending-approvals"],
    queryFn: fetchPendingApprovals,
    refetchInterval: 15000,
  });

  const approveMutation = useMutation({
    mutationFn: approveCalc,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending-approvals"] });
      queryClient.invalidateQueries({ queryKey: ["orchestration-stats"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (calcId: string) => rejectCalc(calcId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending-approvals"] });
    },
  });

  if (!approvals || approvals.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ClipboardCheck className="h-5 w-5" />
          Ke schválení
          <Badge variant="secondary">{approvals.length}</Badge>
        </CardTitle>
        <CardDescription>Auto-kalkulace čekající na schválení</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {approvals.map((a) => (
            <div key={a.id} className="flex items-center justify-between rounded-lg border p-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <a href={`/zakazky/${a.order_id}`} className="font-medium hover:underline">
                    {a.order_number}
                  </a>
                  {a.customer_name && (
                    <span className="text-sm text-muted-foreground truncate">{a.customer_name}</span>
                  )}
                </div>
                <div className="text-sm text-muted-foreground">
                  {a.name} &middot;{" "}
                  <span className="font-medium text-foreground">
                    {a.total_price.toLocaleString("cs-CZ")} Kč
                  </span>
                </div>
                {a.note && (
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{a.note}</p>
                )}
              </div>
              <div className="flex gap-1 ml-3">
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => approveMutation.mutate(a.id)}
                  disabled={approveMutation.isPending}
                >
                  <CheckCircle className="mr-1 h-3 w-3" />
                  Schválit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => rejectMutation.mutate(a.id)}
                  disabled={rejectMutation.isPending}
                >
                  <XCircle className="mr-1 h-3 w-3" />
                  Zamítnout
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

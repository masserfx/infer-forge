"use client";

import { useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Loader2, BarChart3, Coins, Zap, Hash } from "lucide-react";
import { getAITokenUsage } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

type Period = "day" | "month" | "year";

const PERIOD_LABELS: Record<Period, string> = {
  day: "Dnes",
  month: "Tento mesic",
  year: "Tento rok",
};

const CATEGORY_COLORS = [
  "bg-blue-100 text-blue-800",
  "bg-emerald-100 text-emerald-800",
  "bg-purple-100 text-purple-800",
  "bg-amber-100 text-amber-800",
  "bg-rose-100 text-rose-800",
];

export function AITokenUsageDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [period, setPeriod] = useState<Period>("month");

  const { data, isLoading } = useQuery({
    queryKey: ["ai-token-usage", period],
    queryFn: () => getAITokenUsage(period),
    enabled: open,
  });

  const maxCost = data
    ? Math.max(...data.timeline.map((t) => t.cost_czk), 1)
    : 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[750px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Coins className="h-5 w-5 text-amber-500" />
            Vyuziti AI tokenu
          </DialogTitle>
          <DialogDescription>
            Naklady na AI Claude (Anthropic) podle kategorie a obdobi
          </DialogDescription>
        </DialogHeader>

        {/* Period tabs */}
        <div className="flex gap-1 bg-muted rounded-lg p-1">
          {(["day", "month", "year"] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                period === p
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : data ? (
          <div className="space-y-5">
            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg border p-3 text-center">
                <Coins className="h-4 w-4 mx-auto text-amber-500 mb-1" />
                <div className="text-lg font-bold">
                  {formatCurrency(data.total_cost_czk)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Celkove naklady
                </div>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <Zap className="h-4 w-4 mx-auto text-blue-500 mb-1" />
                <div className="text-lg font-bold">
                  {(data.total_tokens / 1000).toFixed(1)}K
                </div>
                <div className="text-xs text-muted-foreground">
                  Celkem tokenu
                </div>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <Hash className="h-4 w-4 mx-auto text-green-500 mb-1" />
                <div className="text-lg font-bold">{data.total_calls}</div>
                <div className="text-xs text-muted-foreground">
                  Pocet volani
                </div>
              </div>
            </div>

            {/* Categories table */}
            <div>
              <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Naklady podle kategorie
              </h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kategorie</TableHead>
                    <TableHead className="text-right">Volani</TableHead>
                    <TableHead className="text-right">Tokeny (in)</TableHead>
                    <TableHead className="text-right">Tokeny (out)</TableHead>
                    <TableHead className="text-right">Naklady</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.categories.map((cat, i) => (
                    <TableRow key={cat.category}>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={CATEGORY_COLORS[i % CATEGORY_COLORS.length]}
                        >
                          {cat.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {cat.calls}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {(cat.tokens_input / 1000).toFixed(1)}K
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {(cat.tokens_output / 1000).toFixed(1)}K
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        {formatCurrency(cat.cost_czk)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Mini bar chart (CSS-only) */}
            <div>
              <h4 className="text-sm font-semibold mb-2">Naklady v case</h4>
              <div className="flex items-end gap-[2px] h-20 bg-muted/30 rounded-lg p-2">
                {data.timeline.map((point, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-primary/70 rounded-t-sm hover:bg-primary transition-colors min-w-[2px]"
                    style={{
                      height: `${Math.max(4, (point.cost_czk / maxCost) * 100)}%`,
                    }}
                    title={`${point.label}: ${formatCurrency(point.cost_czk)} (${point.calls} volani)`}
                  />
                ))}
              </div>
              <div className="flex justify-between text-[10px] text-muted-foreground mt-1 px-2">
                <span>{data.timeline[0]?.label}</span>
                <span>{data.timeline[data.timeline.length - 1]?.label}</span>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            Data nejsou k dispozici
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}

/**
 * Printable A4 report version of AI token usage for /reporting.
 * Opens in a dialog with print button that generates a clean 1-page A4 report.
 */
export function AITokenReportDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [period, setPeriod] = useState<Period>("month");
  const reportRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["ai-token-usage", period],
    queryFn: () => getAITokenUsage(period),
    enabled: open,
  });

  const handlePrint = useCallback(() => {
    if (!reportRef.current) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;

    const content = reportRef.current.innerHTML;
    printWindow.document.write(`<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>INFER FORGE - Report AI nakladu</title>
  <style>
    @page { size: A4 portrait; margin: 1.5cm; }
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { font-size: 11px; color: #1a1a1a; line-height: 1.4; }
    .header { border-bottom: 2px solid #1a1a1a; padding-bottom: 8px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-end; }
    .header h1 { font-size: 20px; font-weight: 700; }
    .header .subtitle { font-size: 13px; color: #666; }
    .header .date { font-size: 10px; color: #666; text-align: right; }
    .summary { display: flex; gap: 12px; margin-bottom: 16px; }
    .summary-card { flex: 1; border: 1px solid #ddd; border-radius: 6px; padding: 10px; text-align: center; }
    .summary-card .value { font-size: 18px; font-weight: 700; }
    .summary-card .label { font-size: 9px; color: #666; text-transform: uppercase; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
    th, td { padding: 6px 8px; text-align: left; border-bottom: 1px solid #eee; font-size: 10px; }
    th { font-weight: 600; background: #f5f5f5; text-transform: uppercase; font-size: 9px; letter-spacing: 0.5px; }
    td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .category-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 9px; font-weight: 500; }
    .cat-0 { background: #dbeafe; color: #1e40af; }
    .cat-1 { background: #d1fae5; color: #065f46; }
    .cat-2 { background: #ede9fe; color: #5b21b6; }
    .cat-3 { background: #fef3c7; color: #92400e; }
    .cat-4 { background: #ffe4e6; color: #9f1239; }
    .bars { display: flex; align-items: flex-end; gap: 1px; height: 60px; margin-bottom: 4px; background: #f9f9f9; border-radius: 4px; padding: 4px; }
    .bar { flex: 1; background: #3b82f6; border-radius: 2px 2px 0 0; min-width: 1px; }
    .bar-labels { display: flex; justify-content: space-between; font-size: 8px; color: #999; }
    .section-title { font-size: 12px; font-weight: 600; margin-bottom: 8px; }
    .footer { margin-top: 20px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 9px; color: #999; display: flex; justify-content: space-between; }
  </style>
</head>
<body>${content}</body>
</html>`);
    printWindow.document.close();
    setTimeout(() => printWindow.print(), 250);
  }, []);

  const today = new Date().toLocaleDateString("cs-CZ", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const maxCost = data
    ? Math.max(...data.timeline.map((t) => t.cost_czk), 1)
    : 1;

  const formatNum = (n: number) =>
    new Intl.NumberFormat("cs-CZ", { style: "currency", currency: "CZK" }).format(n);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-blue-500" />
            Report nakladu na AI
          </DialogTitle>
          <DialogDescription>
            Podrobny report s moznosti tisku na 1 stranu A4
          </DialogDescription>
        </DialogHeader>

        {/* Period tabs + Print button */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1 bg-muted rounded-lg p-1">
            {(["day", "month", "year"] as Period[]).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  period === p
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {PERIOD_LABELS[p]}
              </button>
            ))}
          </div>
          <Button size="sm" onClick={handlePrint} disabled={!data}>
            Vytvorit report a tisknout
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : data ? (
          <>
            {/* On-screen preview */}
            <div className="rounded-lg border p-4 space-y-4 bg-white">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kategorie</TableHead>
                    <TableHead className="text-right">Volani</TableHead>
                    <TableHead className="text-right">Tokeny vstup</TableHead>
                    <TableHead className="text-right">Tokeny vystup</TableHead>
                    <TableHead className="text-right">Naklady (Kc)</TableHead>
                    <TableHead className="text-right">Podil</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.categories.map((cat, i) => (
                    <TableRow key={cat.category}>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={CATEGORY_COLORS[i % CATEGORY_COLORS.length]}
                        >
                          {cat.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {cat.calls}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {cat.tokens_input.toLocaleString("cs-CZ")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {cat.tokens_output.toLocaleString("cs-CZ")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        {formatCurrency(cat.cost_czk)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {data.total_cost_czk > 0
                          ? `${((cat.cost_czk / data.total_cost_czk) * 100).toFixed(1)}%`
                          : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="font-bold border-t-2">
                    <TableCell>Celkem</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {data.total_calls}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {data.categories
                        .reduce((s, c) => s + c.tokens_input, 0)
                        .toLocaleString("cs-CZ")}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {data.categories
                        .reduce((s, c) => s + c.tokens_output, 0)
                        .toLocaleString("cs-CZ")}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(data.total_cost_czk)}
                    </TableCell>
                    <TableCell className="text-right">100%</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>

            {/* Hidden print content */}
            <div ref={reportRef} className="hidden">
              <div className="header">
                <div>
                  <h1>INFER FORGE</h1>
                  <div className="subtitle">
                    Report nakladu na AI &mdash; {PERIOD_LABELS[period]}
                  </div>
                </div>
                <div className="date">Vygenerovano: {today}</div>
              </div>

              <div className="summary">
                <div className="summary-card">
                  <div className="value">{formatNum(data.total_cost_czk)}</div>
                  <div className="label">Celkove naklady</div>
                </div>
                <div className="summary-card">
                  <div className="value">
                    {(data.total_tokens / 1000).toFixed(1)}K
                  </div>
                  <div className="label">Celkem tokenu</div>
                </div>
                <div className="summary-card">
                  <div className="value">{data.total_calls}</div>
                  <div className="label">Pocet volani</div>
                </div>
              </div>

              <div className="section-title">Naklady podle kategorie</div>
              <table>
                <thead>
                  <tr>
                    <th>Kategorie</th>
                    <th style={{ textAlign: "right" }}>Volani</th>
                    <th style={{ textAlign: "right" }}>Tokeny (vstup)</th>
                    <th style={{ textAlign: "right" }}>Tokeny (vystup)</th>
                    <th style={{ textAlign: "right" }}>Naklady (Kc)</th>
                    <th style={{ textAlign: "right" }}>Podil</th>
                  </tr>
                </thead>
                <tbody>
                  {data.categories.map((cat, i) => (
                    <tr key={cat.category}>
                      <td>
                        <span className={`category-badge cat-${i}`}>
                          {cat.category}
                        </span>
                      </td>
                      <td className="num">{cat.calls}</td>
                      <td className="num">
                        {cat.tokens_input.toLocaleString("cs-CZ")}
                      </td>
                      <td className="num">
                        {cat.tokens_output.toLocaleString("cs-CZ")}
                      </td>
                      <td className="num">{formatNum(cat.cost_czk)}</td>
                      <td className="num">
                        {data.total_cost_czk > 0
                          ? `${((cat.cost_czk / data.total_cost_czk) * 100).toFixed(1)}%`
                          : "\u2014"}
                      </td>
                    </tr>
                  ))}
                  <tr style={{ fontWeight: 700, borderTop: "2px solid #333" }}>
                    <td>CELKEM</td>
                    <td className="num">{data.total_calls}</td>
                    <td className="num">
                      {data.categories
                        .reduce((s, c) => s + c.tokens_input, 0)
                        .toLocaleString("cs-CZ")}
                    </td>
                    <td className="num">
                      {data.categories
                        .reduce((s, c) => s + c.tokens_output, 0)
                        .toLocaleString("cs-CZ")}
                    </td>
                    <td className="num">{formatNum(data.total_cost_czk)}</td>
                    <td className="num">100%</td>
                  </tr>
                </tbody>
              </table>

              <div className="section-title">Vyvoj nakladu v case</div>
              <div className="bars">
                {data.timeline.map((point, i) => (
                  <div
                    key={i}
                    className="bar"
                    style={{
                      height: `${Math.max(4, (point.cost_czk / maxCost) * 100)}%`,
                    }}
                  />
                ))}
              </div>
              <div className="bar-labels">
                <span>{data.timeline[0]?.label}</span>
                <span>
                  {data.timeline[Math.floor(data.timeline.length / 2)]?.label}
                </span>
                <span>{data.timeline[data.timeline.length - 1]?.label}</span>
              </div>

              <div className="footer">
                <span>INFER FORGE v0.1.0 | Infer s.r.o. | ICO: 04856562</span>
                <span>AI provider: Anthropic Claude | Model: Sonnet</span>
              </div>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            Data nejsou k dispozici
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}

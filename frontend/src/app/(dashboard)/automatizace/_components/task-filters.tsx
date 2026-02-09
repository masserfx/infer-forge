"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const stageOptions = [
  { value: "all", label: "Všechny fáze" },
  { value: "ingest", label: "Příjem" },
  { value: "classify", label: "Klasifikace" },
  { value: "parse", label: "Parsování" },
  { value: "ocr", label: "OCR" },
  { value: "analyze", label: "Analýza" },
  { value: "orchestrate", label: "Orchestrace" },
  { value: "calculate", label: "Kalkulace" },
  { value: "offer", label: "Nabídka" },
];

const statusOptions = [
  { value: "all", label: "Všechny stavy" },
  { value: "pending", label: "Čeká" },
  { value: "running", label: "Běží" },
  { value: "success", label: "Úspěch" },
  { value: "failed", label: "Chyba" },
  { value: "dlq", label: "DLQ" },
];

const periodOptions = [
  { value: "all", label: "Celé období" },
  { value: "today", label: "Dnes" },
  { value: "week", label: "Tento týden" },
  { value: "month", label: "Tento měsíc" },
];

export interface TaskFilters {
  stage: string;
  status: string;
  period: string;
}

interface TaskFiltersProps {
  filters: TaskFilters;
  onChange: (filters: TaskFilters) => void;
}

export function TaskFiltersBar({ filters, onChange }: TaskFiltersProps) {
  return (
    <div className="flex flex-wrap gap-3">
      <Select
        value={filters.stage}
        onValueChange={(v) => onChange({ ...filters, stage: v })}
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="Fáze" />
        </SelectTrigger>
        <SelectContent>
          {stageOptions.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.status}
        onValueChange={(v) => onChange({ ...filters, status: v })}
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="Stav" />
        </SelectTrigger>
        <SelectContent>
          {statusOptions.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.period}
        onValueChange={(v) => onChange({ ...filters, period: v })}
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="Období" />
        </SelectTrigger>
        <SelectContent>
          {periodOptions.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

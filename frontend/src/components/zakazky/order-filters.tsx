"use client";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ORDER_STATUS_LABELS, type OrderStatus } from "@/types";
import { Search } from "lucide-react";

interface OrderFiltersProps {
  statusFilter: OrderStatus | "all";
  onStatusChange: (value: OrderStatus | "all") => void;
  searchQuery: string;
  onSearchChange: (value: string) => void;
}

export function OrderFilters({
  statusFilter,
  onStatusChange,
  searchQuery,
  onSearchChange,
}: OrderFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:gap-4 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Hledat podle čísla zakázky nebo zákazníka..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9 min-h-[44px]"
        />
      </div>
      <Select value={statusFilter} onValueChange={onStatusChange}>
        <SelectTrigger className="w-full sm:w-[200px] min-h-[44px]">
          <SelectValue placeholder="Filtrovat podle stavu" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Vše</SelectItem>
          {Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => (
            <SelectItem key={value} value={value}>
              {label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

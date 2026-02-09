"use client";

import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getMaterialPrices } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { MaterialPrice } from "@/types";
import { Loader2, Search } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface MaterialComboboxProps {
  value: string;
  onChange: (value: string) => void;
  onSelect: (material: MaterialPrice) => void;
  id?: string;
  required?: boolean;
}

export function MaterialCombobox({
  value,
  onChange,
  onSelect,
  id,
  required,
}: MaterialComboboxProps) {
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<MaterialPrice[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(async (query: string) => {
    if (query.length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    setIsLoading(true);
    try {
      const items = await getMaterialPrices({
        search: query,
        is_active: true,
        limit: 10,
      });
      setResults(items);
      setOpen(items.length > 0);
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(value), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [value, search]);

  const handleSelect = (material: MaterialPrice) => {
    onSelect(material);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverAnchor asChild>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            id={id}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => {
              if (results.length > 0) setOpen(true);
            }}
            className="pl-8"
            placeholder="Hledat materiál..."
            required={required}
            autoComplete="off"
          />
          {isLoading && (
            <Loader2 className="absolute right-2.5 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
          )}
        </div>
      </PopoverAnchor>
      <PopoverContent
        className="w-[var(--radix-popover-trigger-width)] p-0"
        align="start"
        sideOffset={4}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <ScrollArea className="max-h-60">
          {results.length === 0 && !isLoading ? (
            <p className="p-3 text-sm text-muted-foreground text-center">
              Žádné výsledky
            </p>
          ) : (
            <div className="py-1">
              {results.map((material) => (
                <button
                  key={material.id}
                  type="button"
                  className="w-full px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground cursor-pointer transition-colors"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleSelect(material);
                  }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium truncate">
                      {material.name}
                      {material.dimension && ` ${material.dimension}`}
                    </span>
                    <span className="text-xs font-semibold text-primary whitespace-nowrap">
                      {formatCurrency(material.unit_price)}/{material.unit}
                    </span>
                  </div>
                  {(material.material_grade || material.form) && (
                    <div className="flex gap-2 text-xs text-muted-foreground mt-0.5">
                      {material.material_grade && (
                        <span>{material.material_grade}</span>
                      )}
                      {material.form && <span>{material.form}</span>}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

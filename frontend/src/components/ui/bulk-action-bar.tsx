"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, CheckSquare } from "lucide-react";

interface BulkActionBarProps {
  selectedCount: number;
  onClear: () => void;
  children: React.ReactNode;
}

export function BulkActionBar({ selectedCount, onClear, children }: BulkActionBarProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(selectedCount > 0);
  }, [selectedCount]);

  if (!visible) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom-4 duration-200">
      <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3 shadow-lg">
        <div className="flex items-center gap-2 text-sm font-medium">
          <CheckSquare className="h-4 w-4 text-primary" />
          <span>Vybráno {selectedCount} položek</span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          {children}
        </div>
        <div className="h-4 w-px bg-border" />
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

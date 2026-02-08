"use client";

import { KanbanBoard } from "@/components/kanban/kanban-board";
import { useState } from "react";

export default function KanbanPage() {
  const [myOnly, setMyOnly] = useState(false);

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Pipeline zakázek</h1>
          <p className="text-sm sm:text-base text-muted-foreground">
            Přehled zakázek v jednotlivých fázích výroby
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={myOnly}
            onChange={(e) => setMyOnly(e.target.checked)}
            className="rounded border-gray-300 text-primary focus:ring-primary"
          />
          Jen moje zakázky
        </label>
      </div>
      <KanbanBoard />
    </div>
  );
}

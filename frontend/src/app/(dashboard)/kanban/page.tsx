"use client";

import { KanbanBoard } from "@/components/kanban/kanban-board";

export default function KanbanPage() {
  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Pipeline zakázek</h1>
        <p className="text-sm sm:text-base text-muted-foreground">
          Přehled zakázek v jednotlivých fázích výroby
        </p>
      </div>
      <KanbanBoard />
    </div>
  );
}

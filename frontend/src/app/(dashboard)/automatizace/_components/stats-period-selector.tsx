"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface StatsPeriodSelectorProps {
  value: string;
  onChange: (period: string) => void;
}

export function StatsPeriodSelector({ value, onChange }: StatsPeriodSelectorProps) {
  return (
    <Tabs value={value} onValueChange={onChange}>
      <TabsList>
        <TabsTrigger value="today">Dnes</TabsTrigger>
        <TabsTrigger value="week">Týden</TabsTrigger>
        <TabsTrigger value="month">Měsíc</TabsTrigger>
        <TabsTrigger value="all">Celkem</TabsTrigger>
      </TabsList>
    </Tabs>
  );
}

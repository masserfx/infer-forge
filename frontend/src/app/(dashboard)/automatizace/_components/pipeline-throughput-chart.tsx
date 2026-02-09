"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface TimelineBucket {
  bucket: string;
  tasks_count: number;
  success_count: number;
  failed_count: number;
  tokens_used: number;
}

interface PipelineThroughputChartProps {
  data: TimelineBucket[];
  period: string;
}

export function PipelineThroughputChart({ data, period }: PipelineThroughputChartProps) {
  if (!data || data.length === 0) {
    return null;
  }

  const formatted = data.map((d) => ({
    ...d,
    label: period === "today" ? `${d.bucket}:00` : d.bucket,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Průchod pipeline</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={formatted}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip />
            <Legend />
            <Bar dataKey="success_count" name="Úspěch" stackId="a" fill="hsl(var(--chart-2))" />
            <Bar dataKey="failed_count" name="Chyba" stackId="a" fill="hsl(var(--chart-5))" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

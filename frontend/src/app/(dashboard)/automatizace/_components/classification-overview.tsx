"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend, type PieLabelRenderProps } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ClassificationBucket {
  category: string;
  count: number;
  avg_confidence: number;
}

interface ClassificationOverviewProps {
  data: ClassificationBucket[];
}

const categoryLabels: Record<string, string> = {
  poptavka: "Poptávka",
  objednavka: "Objednávka",
  reklamace: "Reklamace",
  dotaz: "Dotaz",
  priloha: "Příloha",
  informace_zakazka: "Info k zakázce",
  faktura: "Faktura",
  obchodni_sdeleni: "Obchodní sdělení",
};

const categoryColors: Record<string, string> = {
  poptavka: "#3b82f6",
  objednavka: "#22c55e",
  reklamace: "#ef4444",
  dotaz: "#f59e0b",
  priloha: "#8b5cf6",
  informace_zakazka: "#06b6d4",
  faktura: "#a855f7",
  obchodni_sdeleni: "#6b7280",
};

export function ClassificationOverview({ data }: ClassificationOverviewProps) {
  if (!data || data.length === 0) {
    return null;
  }

  const chartData = data.map((d) => ({
    name: categoryLabels[d.category] ?? d.category,
    value: d.count,
    confidence: d.avg_confidence,
    color: categoryColors[d.category] ?? "#94a3b8",
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Distribuce klasifikací</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={110}
              paddingAngle={2}
              dataKey="value"
              label={(props: PieLabelRenderProps) => {
                const { name, percent } = props;
                return `${name ?? ""} ${((percent as number) * 100).toFixed(0)}%`;
              }}
              labelLine={false}
            >
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [`${value}x`, "Počet"]}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

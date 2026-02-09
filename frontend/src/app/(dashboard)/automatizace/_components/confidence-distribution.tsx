"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ConfidenceBucket {
  range: string;
  count: number;
}

interface TrendPoint {
  date: string;
  avg_confidence: number;
  email_count: number;
}

interface ConfidenceDistributionProps {
  buckets: ConfidenceBucket[];
  trend: TrendPoint[];
}

export function ConfidenceDistribution({ buckets, trend }: ConfidenceDistributionProps) {
  const hasBuckets = buckets && buckets.length > 0;
  const hasTrend = trend && trend.length > 0;

  if (!hasBuckets && !hasTrend) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Distribuce confidence</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {hasBuckets && (
          <div>
            <p className="mb-2 text-sm text-muted-foreground">Histogram</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={buckets}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" fontSize={11} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" name="Počet" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {hasTrend && (
          <div>
            <p className="mb-2 text-sm text-muted-foreground">Trend confidence po dnech</p>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" fontSize={11} />
                <YAxis domain={[0, 1]} fontSize={12} tickFormatter={(v) => `${Math.round(Number(v) * 100)}%`} />
                <Tooltip
                  formatter={(value) => [`${Math.round(Number(value) * 100)}%`, "Avg confidence"]}
                />
                <Line
                  type="monotone"
                  dataKey="avg_confidence"
                  stroke="hsl(var(--chart-2))"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

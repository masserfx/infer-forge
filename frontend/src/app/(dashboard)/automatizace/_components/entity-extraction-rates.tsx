"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface EntityField {
  field: string;
  extracted_count: number;
  total_count: number;
  rate: number;
}

interface EntityExtractionRatesProps {
  data: EntityField[];
}

const fieldLabels: Record<string, string> = {
  company_name: "Firma",
  ico: "IČO",
  email: "Email",
  phone: "Telefon",
  items: "Položky",
  deadline: "Termín",
  urgency: "Urgence",
  contact_person: "Kontakt",
};

export function EntityExtractionRates({ data }: EntityExtractionRatesProps) {
  if (!data || data.length === 0) {
    return null;
  }

  const chartData = data.map((d) => ({
    name: fieldLabels[d.field] ?? d.field,
    rate: Math.round(d.rate * 100),
    extracted: d.extracted_count,
    total: d.total_count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Úspěšnost extrakce entit</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 100]} unit="%" fontSize={12} />
            <YAxis type="category" dataKey="name" width={80} fontSize={12} />
            <Tooltip
              formatter={(value) => [`${value}%`, "Rozpoznáno"]}
            />
            <Bar dataKey="rate" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={index}
                  fill={entry.rate >= 70 ? "#22c55e" : entry.rate >= 40 ? "#f59e0b" : "#94a3b8"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

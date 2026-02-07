"use client";

import { useQuery } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getDashboardStats, getRevenueReport, getProductionReport, getCustomerReport } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { ORDER_STATUS_COLORS, ORDER_STATUS_LABELS, PRIORITY_COLORS, PRIORITY_LABELS } from "@/types";
import type { OrderStatus, OrderPriority } from "@/types";

function StatCard({ title, value, description }: { title: string; value: string | number; description?: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardContent>
    </Card>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-12">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}

function DashboardTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return <div className="text-center p-12 text-muted-foreground">Žádná data</div>;

  return (
    <div className="space-y-6">
      {/* Stats grid */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Celkem zakázek" value={data.total_orders} />
        <StatCard title="Ve výrobě" value={data.orders_in_production} />
        <StatCard title="Nové zprávy" value={data.new_inbox_messages} />
        <StatCard title="Čeká fakturaci" value={data.pending_invoicing} />
        <StatCard title="Dokumenty" value={data.total_documents} />
        <StatCard title="Kalkulace" value={data.total_calculations} />
        <StatCard title="Celkový obrat" value={formatCurrency(data.total_revenue)} />
        <StatCard
          title="Po termínu"
          value={data.overdue_orders}
          description={data.overdue_orders > 0 ? "Vyžaduje pozornost" : undefined}
        />
      </div>

      {/* Pipeline */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline zakázek</CardTitle>
          <CardDescription>Rozložení zakázek podle stavů</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {data.pipeline.statuses.map((item) => (
            <div key={item.status} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{item.label}</span>
                <span className="text-muted-foreground">
                  {item.count} ({Math.round((item.count / data.pipeline.total_orders) * 100)}%)
                </span>
              </div>
              <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                <div
                  className="bg-primary h-full transition-all"
                  style={{ width: `${(item.count / data.pipeline.total_orders) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function RevenueTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["revenue-report", 12],
    queryFn: () => getRevenueReport(12),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return <div className="text-center p-12 text-muted-foreground">Žádná data</div>;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Celková hodnota kalkulací"
          value={formatCurrency(data.total_calculation_value)}
        />
        <StatCard
          title="Celková hodnota nabídek"
          value={formatCurrency(data.total_offer_value)}
        />
        <StatCard
          title="Schválené kalkulace"
          value={data.approved_calculations}
        />
        <StatCard
          title="Přijaté nabídky"
          value={data.accepted_offers}
        />
      </div>

      {/* Monthly table */}
      <Card>
        <CardHeader>
          <CardTitle>Měsíční trendy</CardTitle>
          <CardDescription>Přehled za posledních 12 měsíců</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Období</TableHead>
                <TableHead className="text-right">Kalkulace</TableHead>
                <TableHead className="text-right">Nabídky</TableHead>
                <TableHead className="text-right">Počet kalkulací</TableHead>
                <TableHead className="text-right">Počet nabídek</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.monthly.map((row) => (
                <TableRow key={row.period}>
                  <TableCell className="font-medium">{row.period}</TableCell>
                  <TableCell className="text-right">{formatCurrency(row.total_calculations)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(row.total_offers)}</TableCell>
                  <TableCell className="text-right">{row.calculations_count}</TableCell>
                  <TableCell className="text-right">{row.offers_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function ProductionTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["production-report"],
    queryFn: getProductionReport,
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return <div className="text-center p-12 text-muted-foreground">Žádná data</div>;

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-5">
        <StatCard title="Ve výrobě" value={data.in_production} />
        <StatCard title="V expedici" value={data.in_expedition} />
        <StatCard
          title="Po termínu"
          value={data.overdue}
          description={data.overdue > 0 ? "Kritický stav" : undefined}
        />
        <StatCard title="Tento týden" value={data.due_this_week} />
        <StatCard title="Tento měsíc" value={data.due_this_month} />
      </div>

      {/* Orders table */}
      <Card>
        <CardHeader>
          <CardTitle>Zakázky ve výrobě</CardTitle>
          <CardDescription>Přehled aktivních zakázek s termíny</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Číslo</TableHead>
                <TableHead>Zákazník</TableHead>
                <TableHead>Stav</TableHead>
                <TableHead>Priorita</TableHead>
                <TableHead>Termín</TableHead>
                <TableHead className="text-right">Dní do termínu</TableHead>
                <TableHead className="text-right">Položky</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.orders.map((order) => {
                const daysColor =
                  order.days_until_due === null
                    ? "text-muted-foreground"
                    : order.days_until_due < 0
                      ? "text-red-600 font-bold"
                      : order.days_until_due < 7
                        ? "text-yellow-600 font-semibold"
                        : "text-green-600";

                return (
                  <TableRow key={order.order_id}>
                    <TableCell>
                      <Link
                        href={`/zakazky/${order.order_id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {order.order_number}
                      </Link>
                    </TableCell>
                    <TableCell>{order.customer_name}</TableCell>
                    <TableCell>
                      <Badge className={ORDER_STATUS_COLORS[order.status as OrderStatus]}>
                        {ORDER_STATUS_LABELS[order.status as OrderStatus]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={PRIORITY_COLORS[order.priority as OrderPriority]}>
                        {PRIORITY_LABELS[order.priority as OrderPriority]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {order.due_date ? new Date(order.due_date).toLocaleDateString("cs-CZ") : "—"}
                    </TableCell>
                    <TableCell className={`text-right ${daysColor}`}>
                      {order.days_until_due !== null ? order.days_until_due : "—"}
                    </TableCell>
                    <TableCell className="text-right">{order.items_count}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function CustomersTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["customer-report", 20],
    queryFn: () => getCustomerReport(20),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return <div className="text-center p-12 text-muted-foreground">Žádná data</div>;

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
        <StatCard title="Celkem zákazníků" value={data.total_customers} />
        <StatCard title="Aktivní zákazníci" value={data.active_customers} />
      </div>

      {/* Top customers table */}
      <Card>
        <CardHeader>
          <CardTitle>Top zákazníci</CardTitle>
          <CardDescription>20 nejvýznamnějších zákazníků podle obratu</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Firma</TableHead>
                <TableHead>IČO</TableHead>
                <TableHead className="text-right">Počet zakázek</TableHead>
                <TableHead className="text-right">Celková hodnota</TableHead>
                <TableHead className="text-right">Aktivní zakázky</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.top_customers.map((customer) => (
                <TableRow key={customer.customer_id}>
                  <TableCell className="font-medium">{customer.company_name}</TableCell>
                  <TableCell>{customer.ico}</TableCell>
                  <TableCell className="text-right">{customer.orders_count}</TableCell>
                  <TableCell className="text-right">{formatCurrency(customer.total_value)}</TableCell>
                  <TableCell className="text-right">{customer.active_orders}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ReportingPage() {
  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Reporting</h1>
        <p className="text-muted-foreground mt-2">Analytika a přehledy zakázek, obratu a výroby</p>
      </div>

      <Tabs defaultValue="prehled" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-grid">
          <TabsTrigger value="prehled">Přehled</TabsTrigger>
          <TabsTrigger value="obrat">Obrat</TabsTrigger>
          <TabsTrigger value="vyroba">Výroba</TabsTrigger>
          <TabsTrigger value="zakaznici">Zákazníci</TabsTrigger>
        </TabsList>

        <TabsContent value="prehled">
          <DashboardTab />
        </TabsContent>

        <TabsContent value="obrat">
          <RevenueTab />
        </TabsContent>

        <TabsContent value="vyroba">
          <ProductionTab />
        </TabsContent>

        <TabsContent value="zakaznici">
          <CustomersTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

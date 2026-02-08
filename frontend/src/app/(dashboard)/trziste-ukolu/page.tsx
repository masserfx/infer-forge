"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Trophy,
  Medal,
  RefreshCw,
  Star,
  HandMetal,
  Package,
  ArrowRight,
  Clock,
  AlertTriangle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getLeaderboard, getOrders, assignOrder } from "@/lib/api";
import { useAuth } from "@/lib/auth-provider";
import { PointsBadge } from "@/components/gamification/points-badge";
import {
  PERIOD_LABELS,
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  PRIORITY_LABELS,
  PRIORITY_COLORS,
} from "@/types";
import type { PointsPeriod, OrderStatus, OrderPriority, Order } from "@/types";
import { cn } from "@/lib/utils";
import Link from "next/link";

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-yellow-100 border-2 border-yellow-500">
        <Medal className="h-6 w-6 text-yellow-600 fill-yellow-400" />
      </div>
    );
  }
  if (rank === 2) {
    return (
      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 border-2 border-gray-400">
        <Medal className="h-6 w-6 text-gray-600 fill-gray-300" />
      </div>
    );
  }
  if (rank === 3) {
    return (
      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-orange-100 border-2 border-orange-400">
        <Medal className="h-6 w-6 text-orange-700 fill-orange-300" />
      </div>
    );
  }
  return (
    <div className="flex items-center justify-center w-10 h-10 rounded-full bg-muted text-muted-foreground font-bold">
      {rank}
    </div>
  );
}

function UserAvatar({
  name,
  isCurrentUser,
}: {
  name: string;
  isCurrentUser?: boolean;
}) {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div
      className={cn(
        "flex items-center justify-center w-10 h-10 rounded-full font-bold text-sm",
        isCurrentUser
          ? "bg-primary text-primary-foreground"
          : "bg-muted text-muted-foreground",
      )}
    >
      {initials}
    </div>
  );
}

function daysUntilDue(dueDate: string | null): number | null {
  if (!dueDate) return null;
  const now = new Date();
  const due = new Date(dueDate);
  return Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function AvailableOrdersSection() {
  const queryClient = useQueryClient();

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders-all"],
    queryFn: () => getOrders({ limit: 200 }),
  });

  const claimMutation = useMutation({
    mutationFn: (orderId: string) => assignOrder(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders-all"] });
      queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
    },
  });

  const unassigned = (orders ?? []).filter(
    (o: Order) => !o.assigned_to && o.status !== "dokonceno",
  );

  if (isLoading) {
    return (
      <Card>
        <CardContent className="text-center p-8 text-muted-foreground">
          Nacitani dostupnych zakazek...
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-orange-500" />
              Dostupne zakazky
            </CardTitle>
            <CardDescription>
              {unassigned.length > 0
                ? `${unassigned.length} ${unassigned.length === 1 ? "zakazka ceka" : "zakazek ceka"} na prevzeti (+3 body)`
                : "Vsechny zakazky jsou prirazeny"}
            </CardDescription>
          </div>
          <Badge variant="secondary" className="text-lg px-3 py-1">
            {unassigned.length}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {unassigned.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Package className="h-10 w-10 mx-auto mb-3 opacity-50" />
            <p>Vsechny zakazky jsou prirazeny. Skvela prace tymu!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {unassigned.map((order: Order) => {
              const days = daysUntilDue(order.due_date);
              const isOverdue = days !== null && days < 0;
              const isUrgent = days !== null && days >= 0 && days <= 3;

              return (
                <div
                  key={order.id}
                  className={cn(
                    "flex items-center gap-4 p-4 rounded-lg border transition-colors hover:bg-muted/50",
                    isOverdue && "border-red-200 bg-red-50/50",
                    isUrgent && !isOverdue && "border-yellow-200 bg-yellow-50/50",
                  )}
                >
                  {/* Status + Priority */}
                  <div className="flex flex-col gap-1">
                    <Badge
                      className={
                        ORDER_STATUS_COLORS[order.status as OrderStatus]
                      }
                    >
                      {ORDER_STATUS_LABELS[order.status as OrderStatus]}
                    </Badge>
                    <Badge
                      variant="outline"
                      className={
                        PRIORITY_COLORS[order.priority as OrderPriority]
                      }
                    >
                      {PRIORITY_LABELS[order.priority as OrderPriority]}
                    </Badge>
                  </div>

                  {/* Order Info */}
                  <div className="flex-1 min-w-0">
                    <Link
                      href={`/zakazky/${order.id}`}
                      className="font-semibold text-primary hover:underline"
                    >
                      {order.number}
                    </Link>
                    <div className="text-sm text-muted-foreground truncate">
                      {order.customer?.company_name ?? "Neznamy zakaznik"}
                      {order.items.length > 0 &&
                        ` — ${order.items.length} ${order.items.length === 1 ? "polozka" : "polozek"}`}
                    </div>
                    {order.note && (
                      <div className="text-xs text-muted-foreground truncate mt-0.5">
                        {order.note}
                      </div>
                    )}
                  </div>

                  {/* Due date */}
                  <div className="hidden sm:flex items-center gap-1.5 text-sm">
                    {order.due_date ? (
                      <>
                        {isOverdue ? (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        ) : (
                          <Clock className="h-4 w-4 text-muted-foreground" />
                        )}
                        <span
                          className={cn(
                            "tabular-nums",
                            isOverdue
                              ? "text-red-600 font-bold"
                              : isUrgent
                                ? "text-yellow-600 font-semibold"
                                : "text-muted-foreground",
                          )}
                        >
                          {new Date(order.due_date).toLocaleDateString("cs-CZ")}
                        </span>
                      </>
                    ) : (
                      <span className="text-muted-foreground text-xs">
                        Bez terminu
                      </span>
                    )}
                  </div>

                  {/* Claim button */}
                  <Button
                    size="sm"
                    onClick={() => claimMutation.mutate(order.id)}
                    disabled={claimMutation.isPending}
                    className="shrink-0"
                  >
                    <HandMetal className="h-4 w-4 mr-1.5" />
                    Prevzit
                    <ArrowRight className="h-3 w-3 ml-1" />
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function LeaderboardPage() {
  const { user } = useAuth();
  const [period, setPeriod] = useState<PointsPeriod>("weekly");

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["leaderboard", period],
    queryFn: () => getLeaderboard({ period, limit: 50 }),
  });

  const currentUserEntry = data?.entries.find((e) => e.user_id === user?.id);

  const periods: PointsPeriod[] = ["daily", "weekly", "monthly", "all_time"];

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Trophy className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Trziste ukolu</h1>
            <p className="text-muted-foreground">
              Prevezmi zakazky, ziskej body, poraz kolegy
            </p>
          </div>
        </div>
        <Button
          onClick={() => refetch()}
          disabled={isRefetching}
          variant="outline"
          size="sm"
        >
          <RefreshCw
            className={cn("h-4 w-4 mr-2", isRefetching && "animate-spin")}
          />
          Obnovit
        </Button>
      </div>

      {/* Available orders to claim */}
      <div className="mb-8">
        <AvailableOrdersSection />
      </div>

      {/* Period Tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {periods.map((p) => (
          <Button
            key={p}
            onClick={() => setPeriod(p)}
            variant={period === p ? "default" : "outline"}
            size="sm"
          >
            {PERIOD_LABELS[p]}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center p-12">
          <div className="text-muted-foreground">Nacitani...</div>
        </div>
      ) : !data || data.entries.length === 0 ? (
        <Card>
          <CardContent className="text-center p-12">
            <Trophy className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              Zatim zadna data pro zvolene obdobi
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Current User Summary */}
          {currentUserEntry && (
            <Card className="border-primary">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-primary" />
                  Vase pozice
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <UserAvatar
                    name={currentUserEntry.user_name}
                    isCurrentUser
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-lg">
                      {currentUserEntry.user_name}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Umisteni #{currentUserEntry.rank}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {currentUserEntry.total_points}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Celkove body
                      </div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold">
                        {currentUserEntry.tasks_completed}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Dokoncene ukoly
                      </div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-purple-600">
                        {currentUserEntry.bonus_points}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Bonusove body
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Leaderboard Entries */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-yellow-500" />
                Zebricek ({PERIOD_LABELS[period]})
              </CardTitle>
              <CardDescription>
                Celkem {data.total_users}{" "}
                {data.total_users === 1 ? "uzivatel" : "uzivatelu"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.entries.map((entry) => {
                  const isCurrentUser = entry.user_id === user?.id;

                  return (
                    <div
                      key={entry.user_id}
                      className={cn(
                        "flex items-center gap-4 p-4 rounded-lg border transition-colors",
                        isCurrentUser
                          ? "bg-primary/5 border-primary"
                          : "bg-card hover:bg-muted/50",
                      )}
                    >
                      <RankBadge rank={entry.rank} />
                      <UserAvatar
                        name={entry.user_name}
                        isCurrentUser={isCurrentUser}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold flex items-center gap-2">
                          {entry.user_name}
                          {isCurrentUser && (
                            <Badge variant="outline" className="text-xs">
                              Vy
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground truncate">
                          {entry.tasks_completed}{" "}
                          {entry.tasks_completed === 1 ? "ukol" : "ukolu"}
                        </div>
                      </div>
                      <div className="hidden md:flex items-center gap-6 text-sm">
                        <div className="text-center">
                          <div className="font-semibold">
                            {entry.points_earned}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Ziskano
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="font-semibold text-purple-600">
                            {entry.bonus_points}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Bonus
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="font-semibold">
                            {entry.tasks_completed}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Ukoly
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <PointsBadge
                          points={entry.total_points}
                          size="lg"
                          variant={entry.rank <= 3 ? "gradient" : "default"}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

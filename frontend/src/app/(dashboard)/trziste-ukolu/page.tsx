"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Trophy, Medal, RefreshCw, Star } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getLeaderboard } from "@/lib/api";
import { useAuth } from "@/lib/auth-provider";
import { PointsBadge } from "@/components/gamification/points-badge";
import { PERIOD_LABELS } from "@/types";
import type { PointsPeriod } from "@/types";
import { cn } from "@/lib/utils";

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

function UserAvatar({ name, isCurrentUser }: { name: string; isCurrentUser?: boolean }) {
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
          : "bg-muted text-muted-foreground"
      )}
    >
      {initials}
    </div>
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

  const handleRefresh = () => {
    refetch();
  };

  const periods: PointsPeriod[] = ["daily", "weekly", "monthly", "all_time"];

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Trophy className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Tržiště úkolů</h1>
            <p className="text-muted-foreground">Výkonnost týmu a motivační body</p>
          </div>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={isRefetching}
          variant="outline"
          size="sm"
        >
          <RefreshCw className={cn("h-4 w-4 mr-2", isRefetching && "animate-spin")} />
          Obnovit
        </Button>
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
          <div className="text-muted-foreground">Načítání...</div>
        </div>
      ) : !data || data.entries.length === 0 ? (
        <Card>
          <CardContent className="text-center p-12">
            <Trophy className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Zatím žádná data pro zvolené období</p>
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
                  Vaše pozice
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <UserAvatar name={currentUserEntry.user_name} isCurrentUser />
                  <div className="flex-1">
                    <div className="font-semibold text-lg">{currentUserEntry.user_name}</div>
                    <div className="text-sm text-muted-foreground">
                      Umístění #{currentUserEntry.rank}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {currentUserEntry.total_points}
                      </div>
                      <div className="text-xs text-muted-foreground">Celkové body</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold">{currentUserEntry.tasks_completed}</div>
                      <div className="text-xs text-muted-foreground">Dokončené úkoly</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-purple-600">
                        {currentUserEntry.bonus_points}
                      </div>
                      <div className="text-xs text-muted-foreground">Bonusové body</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Leaderboard Entries */}
          <Card>
            <CardHeader>
              <CardTitle>Tržiště úkolů ({PERIOD_LABELS[period]})</CardTitle>
              <CardDescription>
                Celkem {data.total_users} {data.total_users === 1 ? "uživatel" : "uživatelů"}
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
                          : "bg-card hover:bg-muted/50"
                      )}
                    >
                      {/* Rank */}
                      <RankBadge rank={entry.rank} />

                      {/* Avatar */}
                      <UserAvatar name={entry.user_name} isCurrentUser={isCurrentUser} />

                      {/* User Info */}
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
                          {entry.tasks_completed} {entry.tasks_completed === 1 ? "úkol" : "úkolů"}
                        </div>
                      </div>

                      {/* Stats */}
                      <div className="hidden md:flex items-center gap-6 text-sm">
                        <div className="text-center">
                          <div className="font-semibold">{entry.points_earned}</div>
                          <div className="text-xs text-muted-foreground">Získáno</div>
                        </div>
                        <div className="text-center">
                          <div className="font-semibold text-purple-600">
                            {entry.bonus_points}
                          </div>
                          <div className="text-xs text-muted-foreground">Bonus</div>
                        </div>
                        <div className="text-center">
                          <div className="font-semibold">{entry.tasks_completed}</div>
                          <div className="text-xs text-muted-foreground">Úkoly</div>
                        </div>
                      </div>

                      {/* Total Points */}
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

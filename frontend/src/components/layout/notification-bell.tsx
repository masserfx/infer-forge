"use client";

import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useNotifications } from "@/lib/notification-provider";
import { formatDistanceToNow } from "date-fns";
import { cs } from "date-fns/locale";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

export function NotificationBell() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const router = useRouter();

  const handleNotificationClick = async (notification: typeof notifications[0]) => {
    if (!notification.read) {
      await markRead(notification.id);
    }
    if (notification.link) {
      router.push(notification.link);
    }
  };

  // Show max 10 notifications
  const displayedNotifications = notifications.slice(0, 10);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative min-w-[44px] min-h-[44px]">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </Badge>
          )}
          <span className="sr-only">Notifikace</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[calc(100vw-2rem)] sm:w-80 p-0" align="end">
        <div className="flex items-center justify-between border-b px-3 sm:px-4 py-3">
          <h3 className="font-semibold text-sm">Notifikace</h3>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
              onClick={markAllRead}
            >
              <span className="hidden sm:inline">Označit vše jako přečtené</span>
              <span className="sm:hidden">Přečíst vše</span>
            </Button>
          )}
        </div>
        <div className="max-h-[60vh] sm:max-h-[400px] overflow-y-auto">
          {displayedNotifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center text-muted-foreground">
              <Bell className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">Žádné notifikace</p>
            </div>
          ) : (
            <div className="divide-y">
              {displayedNotifications.map((notification) => (
                <button
                  key={notification.id}
                  onClick={() => handleNotificationClick(notification)}
                  className={cn(
                    "w-full px-3 sm:px-4 py-3 text-left hover:bg-accent transition-colors min-h-[44px]",
                    !notification.read && "bg-muted/50",
                  )}
                >
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">
                          {notification.title}
                        </p>
                        {!notification.read && (
                          <span className="h-2 w-2 rounded-full bg-primary flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                        {notification.message}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatDistanceToNow(new Date(notification.created_at), {
                          addSuffix: true,
                          locale: cs,
                        })}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        {notifications.length > 10 && (
          <div className="border-t px-3 sm:px-4 py-3">
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-xs min-h-[44px]"
              onClick={() => router.push("/notifikace")}
            >
              Zobrazit všechny notifikace
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}

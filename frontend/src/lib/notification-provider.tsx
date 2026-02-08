"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { toast } from "sonner";
import { useWebSocket } from "@/lib/use-websocket";
import {
  getNotifications,
  getAuthToken,
  markNotificationRead as apiMarkRead,
  markAllNotificationsRead as apiMarkAllRead,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-provider";
import type { Notification } from "@/types";

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  isConnected: boolean;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(
  undefined,
);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const { lastMessage, isConnected } = useWebSocket();
  const processedMessageIdsRef = useRef(new Set<string>());
  const { isAuthenticated } = useAuth();

  // Fetch initial notifications only when authenticated
  useEffect(() => {
    if (!isAuthenticated) return;

    const loadNotifications = async () => {
      const token = getAuthToken();
      if (!token) return;

      try {
        const result = await getNotifications({ limit: 20 });
        setNotifications(result.items);
        setUnreadCount(result.unread_count);
      } catch (error) {
        console.error("Failed to load notifications:", error);
      }
    };

    loadNotifications();
  }, [isAuthenticated]);

  // Process lastMessage when it changes
  useEffect(() => {
    if (!lastMessage) return;

    // Prevent duplicate processing
    if (processedMessageIdsRef.current.has(lastMessage.id)) {
      return;
    }
    processedMessageIdsRef.current.add(lastMessage.id);

    // Use microtask queue to avoid synchronous setState in effect
    queueMicrotask(() => {
      // Prepend new notification to list
      setNotifications((prev) => [lastMessage, ...prev]);

      // Increment unread count if notification is unread
      if (!lastMessage.read) {
        setUnreadCount((prev) => prev + 1);
      }

      // Show toast notification
      toast(lastMessage.title, {
        description: lastMessage.message,
        action: lastMessage.link
          ? {
              label: "Zobrazit",
              onClick: () => {
                window.location.href = lastMessage.link!;
              },
            }
          : undefined,
      });
    });
  }, [lastMessage]);

  const markRead = async (id: string) => {
    try {
      await apiMarkRead(id);

      // Update local state
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n)),
      );

      // Decrement unread count
      const notification = notifications.find((n) => n.id === id);
      if (notification && !notification.read) {
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
      toast.error("Nepodařilo se označit notifikaci jako přečtenou");
    }
  };

  const markAllRead = async () => {
    try {
      await apiMarkAllRead();

      // Update local state
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);

      toast.success("Všechny notifikace označeny jako přečtené");
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
      toast.error("Nepodařilo se označit všechny notifikace jako přečtené");
    }
  };

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        isConnected,
        markRead,
        markAllRead,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error(
      "useNotifications must be used within a NotificationProvider",
    );
  }
  return context;
}

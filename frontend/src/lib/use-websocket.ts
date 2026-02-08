"use client";

import { useEffect, useRef, useState } from "react";
import { getAuthToken } from "@/lib/api";
import type { Notification } from "@/types";

interface UseWebSocketReturn {
  lastMessage: Notification | null;
  isConnected: boolean;
}

const MAX_RETRIES = 10;
const RECONNECT_DELAY = 5000;
const KEEPALIVE_INTERVAL = 30000;

/**
 * Custom hook for WebSocket connection to backend notifications.
 * Automatically reconnects on disconnect and sends keepalive pings.
 */
export function useWebSocket(): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<Notification | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const keepaliveIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const connect = () => {
      const token = getAuthToken();
      if (!token) {
        console.log("No auth token, skipping WebSocket connection");
        return;
      }

      // Derive WebSocket URL from current location
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws?token=${token}`;

      try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log("WebSocket connected");
          setIsConnected(true);
          reconnectCountRef.current = 0;

          // Start keepalive ping
          keepaliveIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: "ping" }));
            }
          }, KEEPALIVE_INTERVAL);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            // Ignore pong messages
            if (data.type === "pong") {
              return;
            }
            // Parse as notification
            setLastMessage(data as Notification);
          } catch (error) {
            console.error("Failed to parse WebSocket message:", error);
          }
        };

        ws.onerror = (error) => {
          console.error("WebSocket error:", error);
        };

        ws.onclose = () => {
          console.log("WebSocket disconnected");
          setIsConnected(false);

          // Clear keepalive interval
          if (keepaliveIntervalRef.current) {
            clearInterval(keepaliveIntervalRef.current);
            keepaliveIntervalRef.current = null;
          }

          // Attempt reconnect
          if (reconnectCountRef.current < MAX_RETRIES) {
            reconnectCountRef.current++;
            console.log(
              `Reconnecting in ${RECONNECT_DELAY}ms (attempt ${reconnectCountRef.current}/${MAX_RETRIES})`,
            );
            reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
          } else {
            console.error("Max reconnection attempts reached");
          }
        };

        wsRef.current = ws;
      } catch (error) {
        console.error("Failed to create WebSocket connection:", error);
      }
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (keepaliveIntervalRef.current) {
        clearInterval(keepaliveIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  return { lastMessage, isConnected };
}

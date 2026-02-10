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
        return;
      }

      // Derive WebSocket URL from current location (no token in URL)
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws`;

      try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          // Send auth token as first message (not in URL to prevent log leaks)
          ws.send(JSON.stringify({ type: "auth", token }));
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            // Handle auth confirmation
            if (data.type === "auth_ok") {
              setIsConnected(true);
              reconnectCountRef.current = 0;
              // Start keepalive ping after auth
              keepaliveIntervalRef.current = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                  ws.send(JSON.stringify({ type: "ping" }));
                }
              }, KEEPALIVE_INTERVAL);
              return;
            }
            // Ignore pong messages
            if (data.type === "pong") {
              return;
            }
            // Parse as notification
            setLastMessage(data as Notification);
          } catch {
            // Invalid message format
          }
        };

        ws.onerror = () => {
          // Connection error handled by onclose
        };

        ws.onclose = () => {
          setIsConnected(false);

          // Clear keepalive interval
          if (keepaliveIntervalRef.current) {
            clearInterval(keepaliveIntervalRef.current);
            keepaliveIntervalRef.current = null;
          }

          // Attempt reconnect
          if (reconnectCountRef.current < MAX_RETRIES) {
            reconnectCountRef.current++;
            reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
          }
        };

        wsRef.current = ws;
      } catch {
        // Connection creation failed, will not reconnect
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

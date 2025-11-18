import { useEffect, useRef, useState } from "react";

// ---- Types ----

export type WSMessage<T> = {
  type: "state_update";
  state: T;
};

// This will be passed from your page.tsx, so the hook stays reusable
export function useReliableWebSocket<T>(
  url: string,
  onMessage: (msg: WSMessage<T>) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatRef = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const connect = () => {
    // Prevent duplicate sockets
    if (wsRef.current) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setAttempt(0); // Reset retry counter

      // Heartbeat every 10 seconds
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("__ping__");
        }
      }, 10000);
    };

    ws.onmessage = (event) => {
      if (event.data === "__pong__") return;

      try {
        const parsed = JSON.parse(event.data) as WSMessage<T>;
        if (parsed.type === "state_update") {
          onMessage(parsed);
        }
      } catch (err) {
        console.error("WS JSON parse error:", err);
      }
    };

    ws.onerror = () => {
      // We intentionally do nothing — reconnect happens on close
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;

      // Cleanup heartbeat
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }

      // Exponential backoff: 500ms → 1s → 2s → 4s → capped at 5s
      const delay = Math.min(5000, 500 * 2 ** attempt);

      reconnectRef.current = setTimeout(() => {
        setAttempt((prev) => prev + 1);
        connect();
      }, delay);
    };
  };

  // Mount the WebSocket connection
  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    };
    //eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return { isConnected };
}

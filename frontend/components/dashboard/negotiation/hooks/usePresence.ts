"use client";

import { useState, useEffect, useCallback, useRef } from "react";

// ── Types ────────────────────────────────────────────────────────

export interface PresenceUser {
  userId: string;
  name: string;
  avatar: string;
  status: "viewing" | "editing" | "typing" | "idle";
  currentClauseId?: string;
  lastActive: string;
}

interface UsePresenceOptions {
  sessionId: string | null;
  userId: string;
  userName: string;
  userAvatar?: string;
  wsUrl?: string;
}

interface UsePresenceReturn {
  /** Users currently in the session */
  users: PresenceUser[];
  /** Set current clause being viewed/edited */
  setCurrentClause: (clauseId: string | null) => void;
  /** Set typing status */
  setTyping: (isTyping: boolean) => void;
  /** Connection status */
  isConnected: boolean;
}

// ── Hook ─────────────────────────────────────────────────────────

export function usePresence({
  sessionId,
  userId,
  userName,
  userAvatar = "U",
  wsUrl,
}: UsePresenceOptions): UsePresenceReturn {
  const [users, setUsers] = useState<PresenceUser[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const currentClauseRef = useRef<string | null>(null);
  const isTypingRef = useRef(false);

  // Build WebSocket URL — connect to the existing events endpoint
  const getWsUrl = useCallback(() => {
    if (wsUrl) return wsUrl;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const protocol = apiUrl.startsWith("https") ? "wss:" : "ws:";
    const baseHost = apiUrl.replace(/^https?:\/\//, "").replace(/\/api\/v1\/?$/, "");
    // Use the existing /api/v1/ws/events endpoint (no negotiation-specific WS)
    return `${protocol}//${baseHost}/api/v1/ws/events`;
  }, [wsUrl]);

  useEffect(() => {
    if (!sessionId) return;

    let reconnectTimer: ReturnType<typeof setTimeout>;
    let isCancelled = false;

    const connect = () => {
      try {
        const url = getWsUrl();
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isCancelled) { ws.close(); return; }
          setIsConnected(true);
          // The events endpoint requires auth first, then subscribe to topics
          // For now, send a subscribe message for the negotiation session
          ws.send(JSON.stringify({
            type: "subscribe",
            topics: [`negotiation:${sessionId}`, `presence:${sessionId}`],
          }));
          // Also send presence join
          ws.send(JSON.stringify({
            type: "presence:join",
            userId,
            userName,
            userAvatar,
            sessionId,
          }));
        };

        ws.onmessage = (event) => {
          if (isCancelled) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === "presence:update" || data.type === "presence:users") {
              setUsers(data.users || []);
            } else if (data.type === "presence:join" || data.type === "presence:leave") {
              // Will be handled by presence:update
            }
          } catch { /* ignore malformed messages */ }
        };

        ws.onclose = () => {
          if (isCancelled) return;
          setIsConnected(false);
          // Reconnect after 3 seconds
          reconnectTimer = setTimeout(connect, 3000);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        // WebSocket not available — silently degrade
        setIsConnected(false);
      }
    };

    connect();

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "presence:heartbeat",
          userId,
          currentClauseId: currentClauseRef.current,
          isTyping: isTypingRef.current,
        }));
      }
    }, 15000);

    return () => {
      isCancelled = true;
      clearInterval(heartbeat);
      clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setIsConnected(false);
    };
  }, [sessionId, userId, userName, userAvatar, getWsUrl]);

  // Send clause change
  const setCurrentClause = useCallback(
    (clauseId: string | null) => {
      currentClauseRef.current = clauseId;
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "presence:clause",
          userId,
          clauseId,
        }));
      }
    },
    [userId],
  );

  // Send typing status
  const setTyping = useCallback(
    (isTyping: boolean) => {
      isTypingRef.current = isTyping;
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "presence:typing",
          userId,
          isTyping,
        }));
      }
    },
    [userId],
  );

  return {
    users,
    setCurrentClause,
    setTyping,
    isConnected,
  };
}

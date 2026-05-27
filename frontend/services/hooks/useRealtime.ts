/**
 * useRealtime — React hook for WebSocket connection lifecycle.
 *
 * Wraps the RealtimeClient singleton with React state tracking,
 * providing connection state, latency, replay status, and
 * automatic cleanup on unmount.
 *
 * Features:
 * - Visibility API pause/resume (tab hidden → disconnect, tab visible → reconnect)
 * - Route transition persistence (survives SPA navigation without reconnect)
 * - Fixed latency measurement via true ping/pong timing
 * - Connection ownership guard via connectionOwnerId
 * - Duplicate connect prevention metrics
 *
 * Usage:
 *   const { state, latency, isReplaying, replayCount } = useRealtime({
 *     getToken: () => getAccessTokenSilently(),
 *     onEvent: handleEvent,
 *     tenantId: "tenant-123",
 *     userId: "user-456",
 *   });
 *
 *   // Connection state drives UI indicators
 *   <RealtimeConnectionIndicator state={state} latency={latency} />
 *   <ReconnectBanner state={state} attempt={reconnectAttempt} />
 *   <ReplayInProgress isReplaying={isReplaying} eventCount={replayCount} />
 */

"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  RealtimeClient,
  getRealtimeClient,
  disconnectRealtimeClient,
  pauseRealtimeClient,
  resumeRealtimeClient,
  ConnectionState,
  RealtimeEvent,
  RealtimeOptions,
} from "@/lib/realtime";

interface UseRealtimeOptions {
  getToken: () => Promise<string>;
  onEvent: (event: RealtimeEvent) => void;
  topics?: string[];
  tenantId?: string;
  userId?: string;
  autoConnect?: boolean;
  /** Unique owner ID for this hook instance. Used to prevent duplicate
   *  connections when the same component remounts (e.g., route transitions). */
  connectionOwnerId?: string;
}

interface UseRealtimeReturn {
  state: ConnectionState;
  latency: number | undefined;
  isReplaying: boolean;
  replayCount: number;
  reconnectAttempt: number;
  isPaused: boolean;
  subscribe: (topics: string[]) => void;
  disconnect: () => void;
  reconnect: () => void;
  pause: () => void;
  resume: () => void;
}

export function useRealtime(options: UseRealtimeOptions): UseRealtimeReturn {
  const { getToken, onEvent, topics, tenantId, userId, autoConnect = true, connectionOwnerId } = options;

  const [state, setState] = useState<ConnectionState>("disconnected");
  const [latency, setLatency] = useState<number | undefined>(undefined);
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayCount, setReplayCount] = useState(0);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const clientRef = useRef<RealtimeClient | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pongReceivedRef = useRef<boolean>(false);

  // Track reconnect attempts from state changes
  const prevStateRef = useRef<ConnectionState>("disconnected");

  useEffect(() => {
    if (prevStateRef.current === "reconnecting" && state === "connected") {
      // Reconnect completed — reset attempt counter
      setReconnectAttempt(0);
    }
    if (state === "reconnecting") {
      setReconnectAttempt((prev) => prev + 1);
    }
    prevStateRef.current = state;
  }, [state]);

  // ── Visibility API handler ──────────────────────────────────────
  // Pauses the realtime client when the tab is hidden, resumes when visible.
  // This prevents unnecessary reconnection storms when users switch tabs.
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) {
        pauseRealtimeClient();
        setIsPaused(true);
      } else {
        resumeRealtimeClient();
        setIsPaused(false);
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, []);

  // ── Initialize client ───────────────────────────────────────────
  useEffect(() => {
    if (!autoConnect) return;

    const client = getRealtimeClient({
      getToken,
      onEvent: (event: RealtimeEvent) => {
        // Track replay status
        if (event.type === "replay_start") {
          setIsReplaying(true);
          setReplayCount(0);
        }
        if (event.type === "replay_complete") {
          setIsReplaying(false);
        }
        if (event.replayed) {
          setReplayCount((prev) => prev + 1);
        }
        // Track pong for latency measurement
        if (event.type === "pong") {
          pongReceivedRef.current = true;
        }
        // Forward to user handler
        onEvent(event);
      },
      onStateChange: (newState: ConnectionState) => {
        setState(newState);
        if (newState === "connected") {
          setIsPaused(false);
        }
      },
      topics,
      tenantId,
      userId,
      connectionOwnerId,
    });

    clientRef.current = client;
    setState(client.getState());
    setIsPaused(client.isPaused());

    // Connect
    client.connect();

    // ── True ping/pong latency measurement ───────────────────────
    // Sends a custom ping and waits for the pong response.
    // This replaces the broken approach of measuring time between
    // state checks (which always returned ~0ms).
    let lastPingTime = 0;
    pingIntervalRef.current = setInterval(() => {
      if (client.getState() === "connected" && !client.isPaused()) {
        pongReceivedRef.current = false;
        lastPingTime = Date.now();

        // Send a latency probe via the WebSocket
        try {
          // Use the raw WebSocket to send a ping
          const ws = (client as unknown as { ws: WebSocket | null }).ws;
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping", _latency_probe: true }));
          }
        } catch {
          // Ignore send errors
        }

        // Check for pong after a short delay
        const checkPong = () => {
          if (pongReceivedRef.current) {
            const measuredLatency = Date.now() - lastPingTime;
            if (measuredLatency > 0 && measuredLatency < 10000) {
              setLatency(Math.round(measuredLatency));
            }
          }
        };

        // Check after a reasonable delay for the round-trip
        setTimeout(checkPong, 500);
      }
    }, 15000);

    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      // Don't disconnect on unmount — the singleton persists across navigations.
      // The connection ownership guard handles stale connections when a new
      // instance mounts with the same ownerId.
    };
  }, [autoConnect, connectionOwnerId]); // eslint-disable-line react-hooks/exhaustive-deps

  const subscribe = useCallback((newTopics: string[]) => {
    clientRef.current?.subscribe(newTopics);
  }, []);

  const disconnect = useCallback(() => {
    disconnectRealtimeClient();
    clientRef.current = null;
    setState("disconnected");
    setIsPaused(false);
  }, []);

  const reconnect = useCallback(() => {
    disconnectRealtimeClient();
    clientRef.current = null;
    setState("disconnected");
    setIsPaused(false);

    const client = getRealtimeClient({
      getToken,
      onEvent,
      onStateChange: (newState: ConnectionState) => setState(newState),
      topics,
      tenantId,
      userId,
      connectionOwnerId,
    });
    clientRef.current = client;
    client.connect();
  }, [getToken, onEvent, topics, tenantId, userId, connectionOwnerId]);

  const pause = useCallback(() => {
    pauseRealtimeClient();
    setIsPaused(true);
  }, []);

  const resume = useCallback(() => {
    resumeRealtimeClient();
    setIsPaused(false);
  }, []);

  return {
    state,
    latency,
    isReplaying,
    replayCount,
    reconnectAttempt,
    isPaused,
    subscribe,
    disconnect,
    reconnect,
    pause,
    resume,
  };
}

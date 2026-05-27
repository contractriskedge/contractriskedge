/**
 * useAdaptivePolling — WebSocket-aware adaptive polling hook.
 *
 * Replaces aggressive fixed-interval polling with an adaptive strategy
 * that respects the realtime connection state:
 *
 * - Connected → poll every 60–120s (background refresh only)
 * - Reconnecting → poll every 10s (fallback while WS is down)
 * - Failed/Disconnected → poll every 5s (degraded mode)
 * - Processing upload → exponential backoff, not fixed interval
 *
 * When the WebSocket is connected and delivering events, polling is
 * reduced to a minimum since realtime updates drive the UI.
 *
 * Usage:
 *   // Instead of:
 *   const { data } = useQuery({
 *     queryKey: ['status', id],
 *     queryFn: () => fetchStatus(id),
 *     refetchInterval: 2000, // Aggressive fixed polling
 *   });
 *
 *   // Use:
 *   const { data } = useQuery({
 *     queryKey: ['status', id],
 *     queryFn: () => fetchStatus(id),
 *     refetchInterval: adaptiveInterval({
 *       connected: 120_000,   // 2 min when WS connected
 *       reconnecting: 10_000, // 10s during reconnect
 *       disconnected: 5_000,  // 5s when WS is down
 *       processing: {         // Exponential backoff during active processing
 *         base: 2_000,
 *         max: 30_000,
 *         multiplier: 1.5,
 *       },
 *     }),
 *   });
 */

"use client";

import { useRef, useCallback } from "react";
import type { ConnectionState } from "@/lib/realtime";

// ── Types ─────────────────────────────────────────────────────────

export type AdaptivePollingConfig = {
  /** Poll interval in ms when WebSocket is connected. Default: 120000 */
  connected?: number;
  /** Poll interval in ms during reconnection. Default: 10000 */
  reconnecting?: number;
  /** Poll interval in ms when disconnected/failed. Default: 5000 */
  disconnected?: number;
  /** Exponential backoff config for active processing states. */
  processing?: {
    /** Initial poll interval in ms. Default: 2000 */
    base?: number;
    /** Maximum poll interval in ms. Default: 30000 */
    max?: number;
    /** Multiplier applied each poll cycle. Default: 1.5 */
    multiplier?: number;
  };
};

type PollContext = {
  /** Current realtime connection state. */
  connectionState: ConnectionState;
  /** Whether the resource is in an active processing state. */
  isProcessing: boolean;
  /** Number of consecutive polls since processing started. */
  pollCount: number;
};

// ── Defaults ──────────────────────────────────────────────────────

const DEFAULTS: Required<AdaptivePollingConfig> = {
  connected: 120_000,
  reconnecting: 10_000,
  disconnected: 5_000,
  processing: {
    base: 2_000,
    max: 30_000,
    multiplier: 1.5,
  },
};

// ── Adaptive Interval Factory ─────────────────────────────────────

/**
 * Creates a refetchInterval function for TanStack Query that adapts
 * based on the realtime connection state and processing status.
 *
 * Returns `false` when connected and not processing (stops polling
 * entirely since WebSocket will push updates).
 *
 * Usage:
 *   refetchInterval: adaptiveInterval({ connected: 60_000 })
 */
export function adaptiveInterval(config: AdaptivePollingConfig = {}) {
  const cfg = { ...DEFAULTS, ...config };
  const procCfg = { ...DEFAULTS.processing, ...cfg.processing };

  return (query: { state: { data: unknown } }): number | false => {
    // This function is called by TanStack Query with the query state.
    // We need to get the connection state from the global realtime client.
    // Since we can't use hooks here, we read from the module-level state.

    // If we have data and WebSocket is connected, poll very infrequently
    // The realtime events will invalidate the cache when updates occur
    if (query.state.data) {
      const connectionState = getGlobalConnectionState();
      if (connectionState === "connected") {
        return false; // Stop polling — WebSocket will push updates
      }
      if (connectionState === "reconnecting") {
        return cfg.reconnecting;
      }
      return cfg.disconnected;
    }

    // No data yet — use the default for initial fetch
    return cfg.disconnected;
  };
}

// ── Processing Poll Interval ──────────────────────────────────────

/**
 * Creates a refetchInterval function with exponential backoff for
 * active processing states. Call `incrementPollCount()` when the
 * processing state is detected to advance the backoff.
 *
 * Usage:
 *   const { pollCount, incrementPollCount } = usePollCounter();
 *
 *   refetchInterval: processingInterval(pollCount)
 */
export function processingInterval(
  pollCount: number,
  config: { base?: number; max?: number; multiplier?: number } = {},
): number | false {
  const base = config.base ?? 2_000;
  const max = config.max ?? 30_000;
  const multiplier = config.multiplier ?? 1.5;

  // Exponential backoff: base * multiplier^pollCount
  const delay = Math.min(base * Math.pow(multiplier, pollCount), max);
  return Math.round(delay);
}

// ── Poll Counter Hook ─────────────────────────────────────────────

/**
 * Hook that tracks poll count for exponential backoff.
 * Automatically resets when the component unmounts or when
 * explicitly reset.
 *
 * Usage:
 *   const { pollCount, incrementPollCount, resetPollCount } = usePollCounter();
 */
export function usePollCounter() {
  const pollCountRef = useRef(0);

  const incrementPollCount = useCallback(() => {
    pollCountRef.current += 1;
    return pollCountRef.current;
  }, []);

  const resetPollCount = useCallback(() => {
    pollCountRef.current = 0;
  }, []);

  return {
    pollCount: pollCountRef.current,
    incrementPollCount,
    resetPollCount,
  };
}

// ── Global Connection State Tracking ──────────────────────────────
//
// The RealtimeClient updates this module-level variable on state changes.
// This allows the adaptiveInterval factory to read the current connection
// state without needing a React hook context.

let _globalConnectionState: ConnectionState = "disconnected";

export function setGlobalConnectionState(state: ConnectionState): void {
  _globalConnectionState = state;
}

export function getGlobalConnectionState(): ConnectionState {
  return _globalConnectionState;
}

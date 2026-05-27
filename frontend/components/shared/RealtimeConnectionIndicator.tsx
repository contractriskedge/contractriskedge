/**
 * RealtimeConnectionIndicator — Live WebSocket connection status badge.
 *
 * Displays the current connection state of the realtime WebSocket client.
 * Integrates with the RealtimeClient's onStateChange callback.
 *
 * States:
 *   connected    → Green dot + "Live"
 *   connecting   → Yellow pulse + "Connecting..."
 *   reconnecting → Orange pulse + "Reconnecting..."
 *   disconnected → Gray dot + "Disconnected"
 *   failed       → Red dot + "Failed"
 *
 * Usage:
 *   <RealtimeConnectionIndicator state={client.getState()} latency={client.getLatency?.()} />
 */

"use client";

import React from "react";
import { motion } from "framer-motion";
import { Wifi, WifiOff, Loader2, AlertTriangle } from "lucide-react";

export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "failed";

interface Props {
  state: ConnectionState;
  latency?: number; // milliseconds, if available
  className?: string;
}

const stateConfig: Record<
  ConnectionState,
  { bg: string; dot: string; label: string; icon: React.ReactNode; pulse: boolean }
> = {
  connected: {
    bg: "bg-green-50 dark:bg-green-900/20",
    dot: "bg-green-500",
    label: "Live",
    icon: <Wifi className="w-3 h-3 text-green-600 dark:text-green-400" />,
    pulse: false,
  },
  connecting: {
    bg: "bg-yellow-50 dark:bg-yellow-900/20",
    dot: "bg-yellow-500",
    label: "Connecting...",
    icon: <Loader2 className="w-3 h-3 text-yellow-600 dark:text-yellow-400 animate-spin" />,
    pulse: true,
  },
  reconnecting: {
    bg: "bg-orange-50 dark:bg-orange-900/20",
    dot: "bg-orange-500",
    label: "Reconnecting...",
    icon: <Loader2 className="w-3 h-3 text-orange-600 dark:text-orange-400 animate-spin" />,
    pulse: true,
  },
  disconnected: {
    bg: "bg-gray-50 dark:bg-gray-800",
    dot: "bg-gray-400",
    label: "Disconnected",
    icon: <WifiOff className="w-3 h-3 text-gray-500 dark:text-gray-400" />,
    pulse: false,
  },
  failed: {
    bg: "bg-red-50 dark:bg-red-900/20",
    dot: "bg-red-500",
    label: "Connection Failed",
    icon: <AlertTriangle className="w-3 h-3 text-red-600 dark:text-red-400" />,
    pulse: false,
  },
};

export function RealtimeConnectionIndicator({ state, latency, className = "" }: Props) {
  const cfg = stateConfig[state] ?? stateConfig.disconnected;

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${cfg.bg} ${className}`}
      title={`WebSocket: ${cfg.label}${latency != null ? ` (${latency}ms latency)` : ""}`}
    >
      {cfg.pulse ? (
        <motion.span
          className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`}
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        />
      ) : (
        <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      )}
      {cfg.icon}
      <span className="hidden sm:inline">{cfg.label}</span>
      {latency != null && state === "connected" && (
        <span className="text-[10px] text-gray-400 ml-0.5 tabular-nums">
          {latency}ms
        </span>
      )}
    </div>
  );
}

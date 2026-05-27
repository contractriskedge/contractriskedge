/**
 * ReconnectBanner — Visual notification during WebSocket reconnection.
 *
 * Shows a banner at the top of the page when the realtime connection
 * is lost and reconnection is in progress. Auto-dismisses when
 * connection is restored.
 *
 * Usage:
 *   <ReconnectBanner state={connectionState} attempt={3} maxAttempts={10} />
 */

"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { WifiOff, RefreshCw, AlertTriangle } from "lucide-react";

export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "failed";

interface Props {
  state: ConnectionState;
  attempt?: number;
  maxAttempts?: number;
  onDismiss?: () => void;
}

export function ReconnectBanner({ state, attempt = 0, maxAttempts = 10, onDismiss }: Props) {
  const isVisible = state === "reconnecting" || state === "disconnected" || state === "failed";

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          className={`overflow-hidden ${
            state === "failed"
              ? "bg-red-50 border-b border-red-200 dark:bg-red-900/20 dark:border-red-800"
              : "bg-amber-50 border-b border-amber-200 dark:bg-amber-900/20 dark:border-amber-800"
          }`}
        >
          <div className="max-w-7xl mx-auto px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              {state === "failed" ? (
                <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
              ) : (
                <RefreshCw className="w-4 h-4 text-amber-600 dark:text-amber-400 animate-spin flex-shrink-0" />
              )}
              <span
                className={
                  state === "failed"
                    ? "text-red-700 dark:text-red-300"
                    : "text-amber-700 dark:text-amber-300"
                }
              >
                {state === "reconnecting" && (
                  <>
                    Reconnecting to server
                    {attempt > 0 && (
                      <span className="text-amber-500 dark:text-amber-400">
                        {" "}(attempt {attempt}/{maxAttempts})
                      </span>
                    )}
                    ...
                  </>
                )}
                {state === "disconnected" && "Connection lost. Attempting to reconnect..."}
                {state === "failed" && (
                  <>
                    Unable to establish realtime connection.{" "}
                    <span className="font-medium">Some features may be unavailable.</span>
                  </>
                )}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {state === "failed" && onDismiss && (
                <button
                  onClick={onDismiss}
                  className="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 underline"
                >
                  Dismiss
                </button>
              )}
              <WifiOff className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

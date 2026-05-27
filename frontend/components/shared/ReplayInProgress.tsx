/**
 * ReplayInProgress — Shows when the WebSocket client is replaying missed events.
 *
 * During replay, the client receives historical events that were missed
 * while disconnected. This indicator shows replay progress and count.
 *
 * Usage:
 *   <ReplayInProgress isReplaying={true} eventCount={42} />
 */

"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { History, ChevronRight } from "lucide-react";

interface Props {
  isReplaying: boolean;
  eventCount?: number;
  onComplete?: () => void;
}

export function ReplayInProgress({ isReplaying, eventCount, onComplete }: Props) {
  return (
    <AnimatePresence>
      {isReplaying && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          className="bg-indigo-50 border border-indigo-200 dark:bg-indigo-900/20 dark:border-indigo-800 rounded-lg px-3 py-2 flex items-center gap-2 text-xs"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            <History className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
          </motion.div>
          <span className="text-indigo-700 dark:text-indigo-300 font-medium">
            Catching up
          </span>
          {eventCount != null && eventCount > 0 && (
            <>
              <ChevronRight className="w-3 h-3 text-indigo-400" />
              <span className="text-indigo-600 dark:text-indigo-400 tabular-nums">
                {eventCount} event{eventCount !== 1 ? "s" : ""}
              </span>
            </>
          )}
          <motion.div
            className="flex-1 h-1 bg-indigo-200 dark:bg-indigo-700 rounded-full overflow-hidden max-w-[80px]"
          >
            <motion.div
              className="h-full bg-indigo-500 rounded-full"
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            />
          </motion.div>
          <span className="text-indigo-400 dark:text-indigo-500">Replaying...</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

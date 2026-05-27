/**
 * DegradedModeBanner — Alert banner when system services are degraded.
 *
 * Shows when one or more backend services are experiencing issues.
 * Supports multiple severity levels and service-specific messaging.
 *
 * Usage:
 *   <DegradedModeBanner
 *     services={[
 *       { name: "AI Analysis", status: "degraded", message: "Higher latency than normal" },
 *       { name: "Search", status: "down", message: "Semantic search temporarily unavailable" },
 *     ]}
 *     onDismiss={() => setDismissed(true)}
 *   />
 */

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, X, ChevronDown, ChevronUp } from "lucide-react";

interface ServiceStatus {
  name: string;
  status: "healthy" | "degraded" | "down";
  message?: string;
}

interface Props {
  services: ServiceStatus[];
  onDismiss?: () => void;
}

const severityColor = {
  healthy: "bg-green-50 border-green-200 text-green-700",
  degraded: "bg-yellow-50 border-yellow-200 text-yellow-700",
  down: "bg-red-50 border-red-200 text-red-700",
};

const severityDot = {
  healthy: "bg-green-500",
  degraded: "bg-yellow-500",
  down: "bg-red-500",
};

export function DegradedModeBanner({ services, onDismiss }: Props) {
  const [expanded, setExpanded] = useState(false);

  const degradedServices = services.filter((s) => s.status !== "healthy");
  if (degradedServices.length === 0) return null;

  const worstStatus = degradedServices.some((s) => s.status === "down")
    ? "down"
    : "degraded";

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      className={`overflow-hidden border-b ${
        worstStatus === "down"
          ? "bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800"
          : "bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <AlertTriangle
              className={`w-4 h-4 flex-shrink-0 ${
                worstStatus === "down"
                  ? "text-red-600 dark:text-red-400"
                  : "text-yellow-600 dark:text-yellow-400"
              }`}
            />
            <span
              className={
                worstStatus === "down"
                  ? "text-red-700 dark:text-red-300 font-medium"
                  : "text-yellow-700 dark:text-yellow-300 font-medium"
              }
            >
              {worstStatus === "down"
                ? "Service disruption detected"
                : "System performance degraded"}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ({degradedServices.length} service{degradedServices.length > 1 ? "s" : ""} affected)
            </span>
          </div>
          <div className="flex items-center gap-2">
            {degradedServices.length > 1 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
              >
                {expanded ? (
                  <>
                    Less <ChevronUp className="w-3 h-3" />
                  </>
                ) : (
                  <>
                    Details <ChevronDown className="w-3 h-3" />
                  </>
                )}
              </button>
            )}
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="mt-2 space-y-1.5 pl-6"
            >
              {degradedServices.map((svc) => (
                <div
                  key={svc.name}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs border ${severityColor[svc.status]}`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${severityDot[svc.status]}`} />
                  <span className="font-medium">{svc.name}</span>
                  {svc.message && (
                    <span className="text-gray-500 dark:text-gray-400">— {svc.message}</span>
                  )}
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

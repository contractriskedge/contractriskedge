/**
 * AnomalyFeedWidget — Real-time operational anomaly feed.
 *
 * Shows:
 * - Stuck workflows
 * - Error spikes
 * - SLA breaches
 * - Unusual patterns
 * - Auto-refresh with severity-coded entries
 * - Acknowledge action
 */

"use client";

import React, { useState } from "react";

interface AnomalyEntry {
  id: string;
  type: "stuck_workflow" | "error_spike" | "sla_breach" | "unusual_pattern";
  severity: "critical" | "high" | "medium" | "low";
  timestamp: string;
  title: string;
  description: string;
  acknowledged: boolean;
}

interface AnomalyFeedWidgetProps {
  anomalies?: any | null;
}

const SEVERITY_CONFIG = {
  critical: { bg: "bg-red-50 dark:bg-red-900/20", dot: "bg-red-500", text: "text-red-700 dark:text-red-300", label: "Critical" },
  high: { bg: "bg-orange-50 dark:bg-orange-900/20", dot: "bg-orange-500", text: "text-orange-700 dark:text-orange-300", label: "High" },
  medium: { bg: "bg-yellow-50 dark:bg-yellow-900/20", dot: "bg-yellow-500", text: "text-yellow-700 dark:text-yellow-300", label: "Medium" },
  low: { bg: "bg-blue-50 dark:bg-blue-900/20", dot: "bg-blue-500", text: "text-blue-700 dark:text-blue-300", label: "Low" },
};

const TYPE_ICONS: Record<string, string> = {
  stuck_workflow: "⏳",
  error_spike: "⚠️",
  sla_breach: "🚨",
  unusual_pattern: "🔍",
};

export function AnomalyFeedWidget({ anomalies: anomaliesData }: AnomalyFeedWidgetProps) {
  const [filter, setFilter] = useState<string>("all");

  // Use anomalies from props when available, otherwise empty
  const anomalies: AnomalyEntry[] = React.useMemo(() => {
    if (!anomaliesData || !Array.isArray(anomaliesData)) return [];
    return anomaliesData.map((a: any, idx: number) => ({
      id: a.id ?? `anomaly-${idx}`,
      type: a.type ?? "unusual_pattern",
      severity: a.severity ?? "low",
      timestamp: a.timestamp ?? "",
      title: a.title ?? "Anomaly",
      description: a.description ?? "",
      acknowledged: a.acknowledged ?? false,
    }));
  }, [anomaliesData]);

  const [localAnomalies, setLocalAnomalies] = useState<AnomalyEntry[]>([]);
  const displayAnomalies = anomalies.length > 0 ? anomalies : localAnomalies;

  const acknowledge = (id: string) => {
    setLocalAnomalies((prev) =>
      prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a))
    );
  };

  const filtered = displayAnomalies.filter((a) => {
    if (filter === "unacknowledged") return !a.acknowledged;
    if (filter === "acknowledged") return a.acknowledged;
    return true;
  });

  const unacknowledgedCount = anomalies.filter((a) => !a.acknowledged).length;

  return (
    <div className="space-y-2">
      {/* ── Filter bar ────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {unacknowledgedCount > 0 ? `${unacknowledgedCount} unacknowledged` : "All clear"}
          </span>
          {unacknowledgedCount > 0 && (
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          )}
        </div>
        <div className="flex gap-1">
          {["all", "unacknowledged", "acknowledged"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 text-[10px] rounded-md ${
                filter === f
                  ? "bg-navy-900 dark:bg-navy-600 text-white"
                  : "text-gray-500 hover:text-navy-700 dark:hover:text-navy-200"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* ── Feed ──────────────────────────────────────────────── */}
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {filtered.length === 0 && (
          <div className="text-center py-6">
            <p className="text-xs text-gray-400">No anomalies matching filter</p>
          </div>
        )}
        {filtered.map((anomaly) => {
          const cfg = SEVERITY_CONFIG[anomaly.severity];
          return (
            <div
              key={anomaly.id}
              className={`px-3 py-2 rounded-lg ${cfg.bg} flex items-start gap-2 ${
                anomaly.acknowledged ? "opacity-60" : ""
              }`}
            >
              <span className="text-sm mt-0.5">{TYPE_ICONS[anomaly.type]}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                  <span className={`text-xs font-medium ${cfg.text}`}>{cfg.label}</span>
                  <span className="text-[10px] text-gray-400">{anomaly.timestamp}</span>
                </div>
                <p className="text-xs font-medium text-navy-900 dark:text-white mt-0.5">
                  {anomaly.title}
                </p>
                <p className="text-[10px] text-gray-500 dark:text-gray-400">
                  {anomaly.description}
                </p>
              </div>
              {!anomaly.acknowledged && (
                <button
                  onClick={() => acknowledge(anomaly.id)}
                  className="px-2 py-0.5 text-[10px] font-medium rounded bg-white dark:bg-navy-700 text-navy-700 dark:text-navy-200 hover:bg-gray-50 dark:hover:bg-navy-600 shrink-0"
                >
                  Acknowledge
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

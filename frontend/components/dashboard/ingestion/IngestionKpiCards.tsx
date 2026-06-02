"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { CompactKpi } from "./types";

const dot: Record<string, string> = {
  critical: "bg-red-500", warning: "bg-amber-500", success: "bg-green-500", info: "bg-blue-500",
};

export function IngestionKpiCards({ metrics, onKpiClick }: { metrics: CompactKpi[]; onKpiClick?: (id: string) => void }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1.5">
      {metrics.map((m) => {
        const TrendIcon = m.trendDirection === "up" ? TrendingUp : m.trendDirection === "down" ? TrendingDown : Minus;
        const isBadUp = m.id === "failed-jobs" || m.id === "processing-queue";
        const tc = (m.trendDirection === "up" && isBadUp) ? "text-red-500" :
          (m.trendDirection === "down" && isBadUp) ? "text-green-500" :
          m.trendDirection === "up" ? "text-green-500" :
          m.trendDirection === "down" ? "text-red-500" : "text-gray-400";
        return (
          <button key={m.id} onClick={() => onKpiClick?.(m.id)} title={m.tooltip}
            className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded px-2.5 py-1.5 text-left hover:border-gray-300 dark:hover:border-navy-600 transition-colors cursor-pointer w-full"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${dot[m.severity]}`} />
                <span className="text-[11px] text-gray-500 dark:text-gray-400 truncate">{m.label}</span>
              </div>
              <div className="flex items-center gap-0.5">
                <TrendIcon className={`w-2.5 h-2.5 ${tc}`} />
                <span className={`text-[9px] font-semibold tabular-nums ${tc}`}>{m.trend > 0 ? "+" : ""}{m.trend}%</span>
              </div>
            </div>
            <p className="text-sm font-bold text-navy-900 dark:text-white tabular-nums tracking-tight leading-tight mt-0.5">{m.value}</p>
          </button>
        );
      })}
    </div>
  );
}


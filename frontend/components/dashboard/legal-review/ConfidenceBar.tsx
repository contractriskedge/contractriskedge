"use client";

import React from "react";

interface ConfidenceBarProps {
  score: number; // 0–1
  showLabel?: boolean;
  size?: "sm" | "md";
}

export function ConfidenceBar({ score, showLabel = true, size = "sm" }: ConfidenceBarProps) {
  const pct = Math.round(Math.min(1, Math.max(0, score)) * 100);
  const barHeight = size === "sm" ? "h-1.5" : "h-2";

  const color =
    pct >= 80 ? "bg-green-500" :
    pct >= 60 ? "bg-emerald-500" :
    pct >= 40 ? "bg-yellow-500" :
    pct >= 20 ? "bg-orange-500" :
    "bg-red-500";

  const label =
    pct >= 80 ? "High confidence" :
    pct >= 60 ? "Good confidence" :
    pct >= 40 ? "Medium confidence" :
    pct >= 20 ? "Low confidence" :
    "Very low confidence";

  return (
    <div className="flex items-center gap-2" role="img" aria-label={label}>
      <div className={`flex-1 ${barHeight} bg-gray-200 rounded-full overflow-hidden`}>
        <div
          className={`${barHeight} rounded-full transition-all duration-500 ease-out ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-gray-500 w-9 text-right tabular-nums">
          {pct}%
        </span>
      )}
    </div>
  );
}

/**
 * DashboardHeader — Shared header for all Sprint 10 dashboards.
 *
 * Provides:
 * - Title + description
 * - Date range selector (24h / 7d / 30d / 90d)
 * - Auto-refresh interval toggle
 * - Export / snapshot button
 * - Fullscreen support indicator
 */

"use client";

import React from "react";

type DateRange = "24h" | "7d" | "30d" | "90d";
type RefreshInterval = 0 | 15 | 30 | 60;

interface DashboardHeaderProps {
  title: string;
  description: string;
  dateRange: DateRange;
  onDateRangeChange: (range: DateRange) => void;
  refreshInterval: RefreshInterval;
  onRefreshIntervalChange: (interval: RefreshInterval) => void;
  onExport: () => void;
}

const DATE_RANGES: { value: DateRange; label: string }[] = [
  { value: "24h", label: "24H" },
  { value: "7d", label: "7D" },
  { value: "30d", label: "30D" },
  { value: "90d", label: "90D" },
];

const REFRESH_INTERVALS: { value: RefreshInterval; label: string }[] = [
  { value: 0, label: "Off" },
  { value: 15, label: "15s" },
  { value: 30, label: "30s" },
  { value: 60, label: "60s" },
];

export function DashboardHeader({
  title,
  description,
  dateRange,
  onDateRangeChange,
  refreshInterval,
  onRefreshIntervalChange,
  onExport,
}: DashboardHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
      {/* ── Title ─────────────────────────────────────────────── */}
      <div className="min-w-0">
        <h1 className="text-xl font-bold text-navy-900 dark:text-white truncate">
          {title}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 truncate">
          {description}
        </p>
      </div>

      {/* ── Controls ──────────────────────────────────────────── */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Date Range */}
        <div className="flex items-center bg-gray-100 dark:bg-navy-700 rounded-lg p-0.5">
          {DATE_RANGES.map((dr) => (
            <button
              key={dr.value}
              onClick={() => onDateRangeChange(dr.value)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                dateRange === dr.value
                  ? "bg-white dark:bg-navy-600 text-navy-900 dark:text-white shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-navy-700 dark:hover:text-navy-200"
              }`}
            >
              {dr.label}
            </button>
          ))}
        </div>

        {/* Auto-refresh */}
        <div className="flex items-center bg-gray-100 dark:bg-navy-700 rounded-lg p-0.5">
          {REFRESH_INTERVALS.map((ri) => (
            <button
              key={ri.value}
              onClick={() => onRefreshIntervalChange(ri.value)}
              className={`px-2 py-1 text-xs font-medium rounded-md transition-colors flex items-center gap-1 ${
                refreshInterval === ri.value
                  ? "bg-white dark:bg-navy-600 text-navy-900 dark:text-white shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-navy-700 dark:hover:text-navy-200"
              }`}
            >
              {ri.value > 0 && (
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              )}
              {ri.label}
            </button>
          ))}
        </div>

        {/* Export */}
        <button
          onClick={onExport}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-900 dark:bg-navy-600 text-white hover:bg-navy-800 dark:hover:bg-navy-500 transition-colors flex items-center gap-1.5"
          title="Export dashboard as PNG"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Export
        </button>
      </div>
    </div>
  );
}

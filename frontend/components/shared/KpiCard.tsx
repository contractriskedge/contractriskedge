/**
 * KpiCard — Unified KPI card with clickable drill-down, last-updated
 * timestamp, and trend indicators.
 *
 * Features:
 * A. Clickable → onClick navigates to the underlying module
 * B. "Last Updated" timestamp → builds confidence in data freshness
 * C. Trend indicators → ▲ +12% / ▼ -8% / No Change
 *
 * Usage:
 *   <KpiCard
 *     title="Active Reviews"
 *     value={42}
 *     subtitle="3 due today"
 *     icon={<FileText className="h-5 w-5 text-white" />}
 *     color="bg-blue-500"
 *     onClick={() => navigateTo("review")}
 *     lastUpdated={new Date()}
 *     trend={{ value: 12, positive: true }}
 *   />
 */

"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus, Clock } from "lucide-react";

// ── Types ───────────────────────────────────────────────────────────────────

export interface TrendData {
  value: number;
  positive: boolean;
  /** Optional label override. Default: "vs last period" */
  label?: string;
}

export interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  /** Click handler for drill-down navigation */
  onClick?: () => void;
  /** Last-updated timestamp for freshness indicator */
  lastUpdated?: Date | string | null;
  /** Trend data for directional indicators */
  trend?: TrendData;
  className?: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 10) return "Just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function parseDate(input: Date | string | null | undefined): Date | null {
  if (!input) return null;
  if (input instanceof Date) return isNaN(input.getTime()) ? null : input;
  const d = new Date(input);
  return isNaN(d.getTime()) ? null : d;
}

// ── Component ───────────────────────────────────────────────────────────────

export function KpiCard({
  title,
  value,
  subtitle,
  icon,
  color,
  onClick,
  lastUpdated,
  trend,
  className = "",
}: KpiCardProps) {
  const parsedDate = parseDate(lastUpdated);
  const displayValue = value === null || value === undefined || value === "NaN" ? "—" : value;

  const card = (
    <div
      onClick={onClick}
      className={`rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all dark:border-gray-700 dark:bg-gray-800 ${
        onClick
          ? "cursor-pointer hover:shadow-md hover:border-navy-300 dark:hover:border-navy-500 active:scale-[0.98]"
          : ""
      } ${className}`}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? "button" : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(); } } : undefined}
    >
      {/* ── Top row: title + icon ── */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">{title}</p>
            {/* ── C. Trend Indicator ── */}
            {trend && (
              <span
                className={`inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                  trend.value === 0
                    ? "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                    : trend.positive
                      ? "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300"
                      : "bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-300"
                }`}
              >
                {trend.value === 0 ? (
                  <Minus className="w-2.5 h-2.5" />
                ) : trend.positive ? (
                  <TrendingUp className="w-2.5 h-2.5" />
                ) : (
                  <TrendingDown className="w-2.5 h-2.5" />
                )}
                {trend.value === 0 ? "No Change" : `${Math.abs(trend.value)}%`}
              </span>
            )}
          </div>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{displayValue}</p>
          {subtitle && (
            <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{subtitle}</p>
          )}
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color} flex-shrink-0 ml-3`}>
          {icon}
        </div>
      </div>

      {/* ── Bottom row: last updated + trend footnote ── */}
      <div className="mt-3 flex items-center justify-between">
        {/* B. Last Updated timestamp */}
        {parsedDate && (
          <div className="flex items-center gap-1 text-[10px] text-gray-400 dark:text-gray-500">
            <Clock className="w-3 h-3" />
            <span>
              Last Updated <span className="font-medium text-gray-500 dark:text-gray-400">{formatTimeAgo(parsedDate)}</span>
            </span>
          </div>
        )}
        {/* Trend footnote */}
        {trend && trend.value !== 0 && (
          <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-auto">
            {trend.label || "vs last period"}
          </span>
        )}
      </div>
    </div>
  );

  return card;
}

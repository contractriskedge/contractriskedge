/**
 * DashboardConsistencyCheck — Validates that KPI counts match
 * the underlying module data.
 *
 * This addresses the requirement:
 *   Dashboard KPI → Open module → Count matches
 *
 * It compares dashboard-level aggregated counts against the actual
 * data from the relevant modules and flags discrepancies.
 */

"use client";

import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, RefreshCw } from "lucide-react";

// ── Types ───────────────────────────────────────────────────────────────────

interface ConsistencyCheckItem {
  label: string;
  dashboardCount: number;
  moduleCount: number;
  moduleName: string;
  status: "match" | "mismatch" | "unchecked";
}

interface DashboardConsistencyCheckProps {
  checks: ConsistencyCheckItem[];
  onRefresh?: () => void;
  className?: string;
}

// ── Component ───────────────────────────────────────────────────────────────

export function DashboardConsistencyCheck({
  checks,
  onRefresh,
  className = "",
}: DashboardConsistencyCheckProps) {
  const [expanded, setExpanded] = useState(false);

  const totalChecks = checks.length;
  const matchedChecks = checks.filter((c) => c.status === "match").length;
  const mismatchedChecks = checks.filter((c) => c.status === "mismatch").length;
  const allMatch = mismatchedChecks === 0;

  if (totalChecks === 0) return null;

  return (
    <div className={`rounded-lg border ${allMatch ? "border-green-200 dark:border-green-800" : "border-amber-200 dark:border-amber-800"} ${className}`}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-navy-850 hover:bg-gray-100 dark:hover:bg-navy-800 transition-colors rounded-t-lg"
      >
        <div className="flex items-center gap-2">
          {allMatch ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
          ) : (
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          )}
          <span className="text-[9px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
            Data Consistency
          </span>
          <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full ${
            allMatch
              ? "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300"
              : "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
          }`}>
            {matchedChecks}/{totalChecks} verified
          </span>
        </div>
        <div className="flex items-center gap-1">
          {onRefresh && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRefresh(); }}
              className="p-1 rounded hover:bg-gray-200 dark:hover:bg-navy-700 text-gray-400"
              title="Re-check consistency"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          )}
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="divide-y divide-gray-50 dark:divide-navy-800">
          {checks.map((check, i) => (
            <div key={i} className="flex items-center justify-between px-3 py-1.5">
              <div className="flex items-center gap-2">
                {check.status === "match" ? (
                  <CheckCircle2 className="w-3 h-3 text-green-500" />
                ) : check.status === "mismatch" ? (
                  <AlertTriangle className="w-3 h-3 text-amber-500" />
                ) : (
                  <span className="w-3 h-3 rounded-full bg-gray-300" />
                )}
                <span className="text-[10px] text-gray-700 dark:text-gray-300">{check.label}</span>
              </div>
              <div className="flex items-center gap-2 text-[9px]">
                <span className="text-gray-500">
                  Dashboard: <span className="font-semibold text-navy-900 dark:text-white">{check.dashboardCount}</span>
                </span>
                <span className="text-gray-300">vs</span>
                <span className="text-gray-500">
                  {check.moduleName}: <span className="font-semibold text-navy-900 dark:text-white">{check.moduleCount}</span>
                </span>
                {check.status === "mismatch" && (
                  <span className="text-amber-600 font-semibold">
                    (Δ {Math.abs(check.dashboardCount - check.moduleCount)})
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

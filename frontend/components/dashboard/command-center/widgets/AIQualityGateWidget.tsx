/**
 * AIQualityGateWidget — AI execution quality monitoring.
 *
 * Shows REAL data from ai_execution_runs table:
 * - AI run success rate (completed / total * 100)
 * - Failed runs count
 * - Average findings per run
 * - Average processing time
 * - Deployment gate status based on success rate threshold
 *
 * No synthetic/hardcoded metrics. When no data exists, shows empty state.
 */

"use client";

import React from "react";

interface QualitySummaryData {
  /** AI run success rate (completed / total * 100) */
  successRate: number;
  /** Total completed AI runs */
  completedRuns: number;
  /** Total failed AI runs */
  failedRuns: number;
  /** Average findings detected per run */
  avgFindingsPerRun: number;
  /** Average processing time in seconds */
  avgProcessingSeconds: number;
  /** Whether the deployment gate is open (success rate >= 80%) */
  deploymentGateOpen: boolean;
  /** Reasons the deployment gate is blocked */
  blockReasons: string[];
}

interface AIQualityGateWidgetProps {
  summary?: QualitySummaryData | null;
}

export function AIQualityGateWidget({ summary }: AIQualityGateWidgetProps) {
  // No data state
  if (!summary) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-navy-700 flex items-center justify-center mb-2">
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No AI quality data available</p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">No AI execution runs found in the current period.</p>
      </div>
    );
  }

  const data = summary;

  return (
    <div className="space-y-3">
      {/* ── Top row: Success Rate + Failed Runs ──────────────── */}
      <div className="flex items-center gap-4">
        {/* Success Rate */}
        <div className="flex-1 p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">AI Run Success</span>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-2xl font-bold ${data.successRate >= 90 ? "text-green-600 dark:text-green-400" : data.successRate >= 80 ? "text-amber-600 dark:text-amber-400" : "text-red-600 dark:text-red-400"}`}>
              {data.successRate}%
            </span>
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${
              data.successRate >= 90
                ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                : data.successRate >= 80
                ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300"
                : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
            }`}>
              {data.completedRuns} runs
            </span>
          </div>
          <p className="text-[10px] text-gray-400 mt-0.5">{data.completedRuns} completed · {data.failedRuns} failed</p>
        </div>

        {/* Avg Processing */}
        <div className="flex-1 p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Processing</span>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-2xl font-bold text-navy-900 dark:text-white">
              {data.avgProcessingSeconds.toFixed(1)}s
            </span>
            <span className="text-xs text-gray-500">avg</span>
          </div>
          <p className="text-[10px] text-gray-400 mt-0.5">{data.avgFindingsPerRun.toFixed(1)} avg findings/run</p>
        </div>
      </div>

      {/* ── Run Details ───────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-navy-700 text-center">
          <span className="text-lg font-bold text-navy-900 dark:text-white">{data.completedRuns}</span>
          <p className="text-[10px] text-gray-500">Completed Runs</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-navy-700 text-center">
          <span className={`text-lg font-bold ${data.failedRuns > 0 ? "text-red-600" : "text-green-600"}`}>
            {data.failedRuns}
          </span>
          <p className="text-[10px] text-gray-500">Failed Runs</p>
        </div>
      </div>

      {/* ── Deployment Gate ───────────────────────────────────── */}
      <div className={`px-3 py-2 rounded-lg border ${
        !data.deploymentGateOpen
          ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
          : "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
      }`}>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium">
            {!data.deploymentGateOpen ? "🚫 Deployment Blocked" : "✅ Deployment Gate Open"}
          </span>
        </div>
        {!data.deploymentGateOpen && data.blockReasons.length > 0 && (
          <ul className="mt-1 space-y-0.5">
            {data.blockReasons.map((reason, i) => (
              <li key={i} className="text-[10px] text-red-600 dark:text-red-400 flex items-center gap-1">
                <span>·</span> {reason}
              </li>
            ))}
          </ul>
        )}
        {data.deploymentGateOpen && (
          <p className="text-[10px] text-green-600 dark:text-green-400 mt-0.5">
            AI execution success rate ({data.successRate}%) meets the 80% threshold.
          </p>
        )}
      </div>
    </div>
  );
}

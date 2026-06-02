/**
 * AIQualityGateWidget — Benchmark results, hallucination rate, gate status.
 *
 * Shows:
 * - Latest benchmark score with pass/fail badge
 * - Hallucination rate trend line (7d)
 * - Regression count with severity breakdown
 * - Deployment block indicators
 */

"use client";

import React from "react";

interface QualitySummaryData {
  latestBenchmarkScore: number;
  benchmarkPassed: boolean;
  hallucinationRate: number;
  hallucinationTrend: number[]; // 7 days
  regressionCount: number;
  criticalRegressions: number;
  majorRegressions: number;
  minorRegressions: number;
  deploymentBlocked: boolean;
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
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Connect to the backend to see AI quality gate metrics.</p>
      </div>
    );
  }

  const data = summary;

  return (
    <div className="space-y-3">
      {/* ── Top row: Score + Hallucination ────────────────────── */}
      <div className="flex items-center gap-4">
        {/* Benchmark Score */}
        <div className="flex-1 p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Benchmark</span>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-2xl font-bold ${data.benchmarkPassed ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
              {data.latestBenchmarkScore}%
            </span>
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${
              data.benchmarkPassed
                ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
            }`}>
              {data.benchmarkPassed ? "Pass" : "Fail"}
            </span>
          </div>
        </div>

        {/* Hallucination Rate */}
        <div className="flex-1 p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Hallucination</span>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-2xl font-bold ${
              data.hallucinationRate < 3 ? "text-green-600 dark:text-green-400" :
              data.hallucinationRate < 5 ? "text-amber-600 dark:text-amber-400" :
              "text-red-600 dark:text-red-400"
            }`}>
              {data.hallucinationRate}%
            </span>
            <span className="text-xs text-gray-500">rate</span>
          </div>
          {/* Mini sparkline */}
          <div className="flex items-end gap-0.5 h-6 mt-1">
            {data.hallucinationTrend.map((val, i) => (
              <div
                key={i}
                className="flex-1 rounded-t"
                style={{
                  height: `${(val / 5) * 100}%`,
                  backgroundColor: val < 3 ? "#10B981" : val < 5 ? "#F59E0B" : "#EF4444",
                  opacity: 0.7 + (i / data.hallucinationTrend.length) * 0.3,
                }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* ── Regressions ───────────────────────────────────────── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Regressions
        </span>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            <span className="text-xs text-navy-900 dark:text-white font-medium">{data.criticalRegressions}</span>
            <span className="text-[10px] text-gray-400">critical</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-orange-500" />
            <span className="text-xs text-navy-900 dark:text-white font-medium">{data.majorRegressions}</span>
            <span className="text-[10px] text-gray-400">major</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-yellow-500" />
            <span className="text-xs text-navy-900 dark:text-white font-medium">{data.minorRegressions}</span>
            <span className="text-[10px] text-gray-400">minor</span>
          </div>
          <span className="text-xs text-gray-500 ml-auto">{data.regressionCount} total</span>
        </div>
      </div>

      {/* ── Deployment Gate ───────────────────────────────────── */}
      <div className={`px-3 py-2 rounded-lg border ${
        data.deploymentBlocked
          ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
          : "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
      }`}>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium">
            {data.deploymentBlocked ? "🚫 Deployment Blocked" : "✅ Deployment Gate Open"}
          </span>
          {data.deploymentBlocked && (
            <span className="text-[10px] text-red-600 dark:text-red-400">
              {data.blockReasons.length} reason{data.blockReasons.length > 1 ? "s" : ""}
            </span>
          )}
        </div>
        {data.deploymentBlocked && data.blockReasons.length > 0 && (
          <ul className="mt-1 space-y-0.5">
            {data.blockReasons.map((reason, i) => (
              <li key={i} className="text-[10px] text-red-600 dark:text-red-400 flex items-center gap-1">
                <span>·</span> {reason}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

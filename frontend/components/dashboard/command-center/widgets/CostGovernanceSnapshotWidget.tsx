/**
 * CostGovernanceSnapshotWidget — Budget status, burn rate, projected overage.
 *
 * Shows:
 * - Budget ring chart (used vs remaining)
 * - Daily burn rate sparkline
 * - Projected overage date
 * - Model tier distribution bar chart
 * - Alert banner at 80%+ (amber) and 95%+ (red)
 */

"use client";

import React from "react";

interface CostDashboardData {
  budgetUsed: number;
  budgetRemaining: number;
  totalBudget: number;
  dailyBurnRate: number;
  projectedOverageDate?: string;
  modelTierDistribution: Record<string, number>;
  isAlerting: boolean;
  alertLevel?: "warning" | "critical";
}

interface CostGovernanceSnapshotWidgetProps {
  dashboard?: CostDashboardData | null;
}

export function CostGovernanceSnapshotWidget({ dashboard }: CostGovernanceSnapshotWidgetProps) {
  // No data state
  if (!dashboard) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-navy-700 flex items-center justify-center mb-2">
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No cost data available</p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Connect to the backend to see cost governance metrics.</p>
      </div>
    );
  }

  const data = dashboard;
  const usagePct = Math.round((data.budgetUsed / data.totalBudget) * 100);
  const remainingPct = 100 - usagePct;

  const isWarning = usagePct >= 80 && usagePct < 95;
  const isCritical = usagePct >= 95;
  const totalTierPct = Object.values(data.modelTierDistribution).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-3">
      {/* ── Alert Banner ─────────────────────────────────────── */}
      {isCritical && (
        <div className="px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-xs font-medium text-red-700 dark:text-red-300">
            ⚠ Budget critical — {usagePct}% used. Projected overage: {data.projectedOverageDate}
          </p>
        </div>
      )}
      {isWarning && !isCritical && (
        <div className="px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-300">
            ⚠ Budget warning — {usagePct}% used. Approaching limit.
          </p>
        </div>
      )}

      {/* ── Budget Ring + Burn Rate ──────────────────────────── */}
      <div className="flex items-center gap-4">
        {/* Ring chart */}
        <div className="relative w-20 h-20 shrink-0">
          <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#E5E7EB" strokeWidth="3" className="dark:stroke-navy-600" />
            <circle
              cx="18" cy="18" r="15.5"
              fill="none"
              stroke={isCritical ? "#EF4444" : isWarning ? "#F59E0B" : "#10B981"}
              strokeWidth="3"
              strokeDasharray={`${usagePct} ${100 - usagePct}`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold text-navy-900 dark:text-white">{usagePct}%</span>
          </div>
        </div>

        {/* Stats */}
        <div className="flex-1 grid grid-cols-2 gap-x-4 gap-y-1">
          <div>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Used</span>
            <p className="text-sm font-semibold text-navy-900 dark:text-white">
              ${data.budgetUsed.toLocaleString()}
            </p>
          </div>
          <div>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Remaining</span>
            <p className="text-sm font-semibold text-navy-900 dark:text-white">
              ${data.budgetRemaining.toLocaleString()}
            </p>
          </div>
          <div>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Daily Burn</span>
            <p className="text-sm font-semibold text-navy-900 dark:text-white">
              ${data.dailyBurnRate.toFixed(2)}
            </p>
          </div>
          <div>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Total Budget</span>
            <p className="text-sm font-semibold text-navy-900 dark:text-white">
              ${data.totalBudget.toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* ── Model Tier Distribution ──────────────────────────── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Model Tier Distribution
        </span>
        <div className="space-y-1">
          {Object.entries(data.modelTierDistribution).map(([tier, pct]) => (
            <div key={tier} className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-16">{tier}</span>
              <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(pct / totalTierPct) * 100}%`,
                    backgroundColor: tier === "Economy" ? "#10B981" : tier === "Standard" ? "#3B82F6" : tier === "Premium" ? "#8B5CF6" : "#6B7280",
                  }}
                />
              </div>
              <span className="text-xs text-navy-900 dark:text-white font-medium w-8 text-right">
                {pct}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Projected Overage ────────────────────────────────── */}
      {data.projectedOverageDate && (
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 pt-1 border-t border-gray-100 dark:border-navy-700">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Projected budget exhaustion: <span className="font-medium text-navy-900 dark:text-white">{data.projectedOverageDate}</span>
        </div>
      )}
    </div>
  );
}

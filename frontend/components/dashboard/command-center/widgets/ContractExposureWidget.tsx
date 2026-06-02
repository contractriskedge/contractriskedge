/**
 * ContractExposureWidget — Total $ at risk, liability concentration, top drivers.
 *
 * Shows:
 * - Total exposure KPI with trend arrow
 * - Top-5 counterparties by liability
 * - Risk driver breakdown as horizontal bar chart
 * - Click navigates to portfolio view
 *
 * Data sourced from executive aggregation layer — no hardcoded defaults.
 */

"use client";

import React from "react";
import type { ContractExposureData } from "@/src/lib/executive/executiveTypes";

interface ContractExposureWidgetProps {
  exposure?: ContractExposureData | null;
}

export function ContractExposureWidget({ exposure }: ContractExposureWidgetProps) {
  if (!exposure) {
    return (
      <div className="flex items-center justify-center h-32 text-xs text-gray-400">
        No exposure data available
      </div>
    );
  }

  const maxLiability = Math.max(...exposure.by_category.map((c) => c.exposure_score), 1);
  const totalDriverContrib = exposure.top_risk_drivers.reduce((a, b) => a + b.contribution_pct, 0);

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(val);

  const concentrationColor = exposure.concentration_risk === "highly_concentrated" ? "text-red-600" :
    exposure.concentration_risk === "concentrated" ? "text-amber-600" : "text-green-600";

  return (
    <div className="space-y-3">
      {/* ── KPI Row ── */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Total Exposure Score</span>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-red-600 dark:text-red-400">
              {exposure.total_exposure_score.toFixed(1)}
            </span>
            <span className={`text-xs ${concentrationColor}`}>
              {exposure.concentration_risk === "highly_concentrated" ? "↑" : exposure.concentration_risk === "concentrated" ? "→" : "↓"}
            </span>
          </div>
          <span className="text-[10px] text-gray-400 capitalize">{exposure.concentration_risk.replace("_", " ")}</span>
        </div>
      </div>

      {/* ── Categories by Exposure ── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Exposure by Category
        </span>
        <div className="space-y-1">
          {exposure.by_category.slice(0, 5).map((cat) => (
            <div key={cat.category} className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate">{cat.category}</span>
              <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(cat.exposure_score / maxLiability) * 100}%`,
                    backgroundColor: cat.avg_severity === "critical" ? "#EF4444" : cat.avg_severity === "high" ? "#F59E0B" : "#10B981",
                  }}
                />
              </div>
              <span className="text-xs text-navy-900 dark:text-white font-medium w-12 text-right">
                {cat.exposure_share_pct.toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Top Risk Drivers ── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Top Risk Drivers
        </span>
        <div className="space-y-1">
          {exposure.top_risk_drivers.slice(0, 5).map((rd) => (
            <div key={rd.clause_type} className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate">{rd.clause_type}</span>
              <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-navy-500 dark:bg-navy-400"
                  style={{ width: `${(rd.contribution_pct / totalDriverContrib) * 100}%` }}
                />
              </div>
              <span className="text-xs text-navy-900 dark:text-white font-medium w-8 text-right">
                {rd.contribution_pct.toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

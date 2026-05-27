/**
 * ContractExposureWidget — Total $ at risk, liability concentration, top drivers.
 *
 * Shows:
 * - Total exposure KPI with trend arrow
 * - Top-5 counterparties by liability
 * - Risk driver breakdown as horizontal bar chart
 * - Click navigates to portfolio view
 */

"use client";

import React from "react";

interface ExposureData {
  totalAtRisk: number;
  avgRiskScore: number;
  trend: "up" | "down" | "stable";
  topCounterparties: { name: string; liability: number; riskScore: number }[];
  topRiskDrivers: { driver: string; contribution: number }[];
}

interface ContractExposureWidgetProps {
  summary?: { contract_exposure?: ExposureData } | null;
}

const DEFAULT_DATA: ExposureData = {
  totalAtRisk: 4_250_000,
  avgRiskScore: 62,
  trend: "up",
  topCounterparties: [
    { name: "Acme Corp", liability: 1_200_000, riskScore: 78 },
    { name: "GlobalTech Inc", liability: 980_000, riskScore: 65 },
    { name: "Prime Suppliers", liability: 750_000, riskScore: 71 },
    { name: "DataSync LLC", liability: 540_000, riskScore: 55 },
    { name: "West Coast Logistics", liability: 420_000, riskScore: 48 },
  ],
  topRiskDrivers: [
    { driver: "Liability Caps", contribution: 32 },
    { driver: "Indemnification", contribution: 24 },
    { driver: "Termination Rights", contribution: 18 },
    { driver: "Data Privacy", contribution: 15 },
    { driver: "Force Majeure", contribution: 11 },
  ],
};

export function ContractExposureWidget({ summary }: ContractExposureWidgetProps) {
  const data = summary?.contract_exposure ?? DEFAULT_DATA;
  const maxLiability = Math.max(...data.topCounterparties.map((c) => c.liability));
  const totalDriverContrib = data.topRiskDrivers.reduce((a, b) => a + b.contribution, 0);

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(val);

  return (
    <div className="space-y-3">
      {/* ── KPI Row ──────────────────────────────────────────── */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Total at Risk</span>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-red-600 dark:text-red-400">
              {formatCurrency(data.totalAtRisk)}
            </span>
            <span className={`text-xs ${
              data.trend === "up" ? "text-red-500" : data.trend === "down" ? "text-green-500" : "text-gray-400"
            }`}>
              {data.trend === "up" ? "↑" : data.trend === "down" ? "↓" : "→"}
            </span>
          </div>
        </div>
        <div className="flex-1">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase">Avg Risk Score</span>
          <div className="flex items-center gap-2">
            <span className={`text-xl font-bold ${
              data.avgRiskScore >= 70 ? "text-red-600 dark:text-red-400" :
              data.avgRiskScore >= 50 ? "text-amber-600 dark:text-amber-400" :
              "text-green-600 dark:text-green-400"
            }`}>
              {data.avgRiskScore}
            </span>
            <span className="text-xs text-gray-500">/100</span>
          </div>
        </div>
      </div>

      {/* ── Top Counterparties ────────────────────────────────── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Top Counterparties by Liability
        </span>
        <div className="space-y-1">
          {data.topCounterparties.map((cp) => (
            <div key={cp.name} className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate">{cp.name}</span>
              <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(cp.liability / maxLiability) * 100}%`,
                    backgroundColor: cp.riskScore >= 70 ? "#EF4444" : cp.riskScore >= 50 ? "#F59E0B" : "#10B981",
                  }}
                />
              </div>
              <span className="text-xs text-navy-900 dark:text-white font-medium w-20 text-right">
                {formatCurrency(cp.liability)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Risk Drivers ──────────────────────────────────────── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Top Risk Drivers
        </span>
        <div className="space-y-1">
          {data.topRiskDrivers.map((rd) => (
            <div key={rd.driver} className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate">{rd.driver}</span>
              <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-navy-500 dark:bg-navy-400"
                  style={{ width: `${(rd.contribution / totalDriverContrib) * 100}%` }}
                />
              </div>
              <span className="text-xs text-navy-900 dark:text-white font-medium w-8 text-right">
                {rd.contribution}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

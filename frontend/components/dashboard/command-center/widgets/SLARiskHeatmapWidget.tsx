/**
 * SLARiskHeatmapWidget — SLA breach probability across reviews.
 *
 * Heatmap grid by department × workflow stage with color intensity
 * indicating breach risk. Click drill-down to affected reviews.
 *
 * Color scale: green (<20%) → yellow (20-50%) → orange (50-80%) → red (>80%)
 */

"use client";

import React, { useState } from "react";

interface SLAPrediction {
  department: string;
  stage: string;
  breachProbability: number; // 0-1
  affectedReviewCount: number;
  reviewIds?: string[];
}

interface SLARiskHeatmapWidgetProps {
  predictions?: SLAPrediction[] | null;
}

function getHeatColor(probability: number): string {
  if (probability < 0.2) return "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300";
  if (probability < 0.5) return "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300";
  if (probability < 0.8) return "bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300";
  return "bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300";
}

function getHeatIntensity(probability: number): string {
  if (probability < 0.2) return "border-green-200 dark:border-green-800";
  if (probability < 0.5) return "border-yellow-200 dark:border-yellow-800";
  if (probability < 0.8) return "border-orange-200 dark:border-orange-800";
  return "border-red-200 dark:border-red-800";
}

const DEFAULT_DEPARTMENTS = ["Commercial", "Procurement", "Legal", "Finance", "Compliance"];
const DEFAULT_STAGES = ["Ingestion", "AI Analysis", "Review", "Approval", "Negotiation"];

const DEFAULT_PREDICTIONS: SLAPrediction[] = [
  { department: "Commercial", stage: "Ingestion", breachProbability: 0.05, affectedReviewCount: 12 },
  { department: "Commercial", stage: "AI Analysis", breachProbability: 0.15, affectedReviewCount: 10 },
  { department: "Commercial", stage: "Review", breachProbability: 0.35, affectedReviewCount: 8 },
  { department: "Commercial", stage: "Approval", breachProbability: 0.55, affectedReviewCount: 5 },
  { department: "Commercial", stage: "Negotiation", breachProbability: 0.45, affectedReviewCount: 3 },
  { department: "Procurement", stage: "Ingestion", breachProbability: 0.08, affectedReviewCount: 15 },
  { department: "Procurement", stage: "AI Analysis", breachProbability: 0.22, affectedReviewCount: 12 },
  { department: "Procurement", stage: "Review", breachProbability: 0.48, affectedReviewCount: 9 },
  { department: "Procurement", stage: "Approval", breachProbability: 0.72, affectedReviewCount: 6 },
  { department: "Procurement", stage: "Negotiation", breachProbability: 0.38, affectedReviewCount: 4 },
  { department: "Legal", stage: "Ingestion", breachProbability: 0.02, affectedReviewCount: 20 },
  { department: "Legal", stage: "AI Analysis", breachProbability: 0.10, affectedReviewCount: 18 },
  { department: "Legal", stage: "Review", breachProbability: 0.28, affectedReviewCount: 14 },
  { department: "Legal", stage: "Approval", breachProbability: 0.42, affectedReviewCount: 10 },
  { department: "Legal", stage: "Negotiation", breachProbability: 0.62, affectedReviewCount: 7 },
  { department: "Finance", stage: "Ingestion", breachProbability: 0.12, affectedReviewCount: 8 },
  { department: "Finance", stage: "AI Analysis", breachProbability: 0.18, affectedReviewCount: 7 },
  { department: "Finance", stage: "Review", breachProbability: 0.32, affectedReviewCount: 5 },
  { department: "Finance", stage: "Approval", breachProbability: 0.58, affectedReviewCount: 4 },
  { department: "Finance", stage: "Negotiation", breachProbability: 0.25, affectedReviewCount: 2 },
  { department: "Compliance", stage: "Ingestion", breachProbability: 0.03, affectedReviewCount: 6 },
  { department: "Compliance", stage: "AI Analysis", breachProbability: 0.08, affectedReviewCount: 5 },
  { department: "Compliance", stage: "Review", breachProbability: 0.15, affectedReviewCount: 4 },
  { department: "Compliance", stage: "Approval", breachProbability: 0.22, affectedReviewCount: 3 },
  { department: "Compliance", stage: "Negotiation", breachProbability: 0.18, affectedReviewCount: 2 },
];

export function SLARiskHeatmapWidget({ predictions }: SLARiskHeatmapWidgetProps) {
  const [selectedCell, setSelectedCell] = useState<SLAPrediction | null>(null);

  const data = predictions ?? DEFAULT_PREDICTIONS;
  const departments = [...new Set(data.map((p) => p.department))];
  const stages = [...new Set(data.map((p) => p.stage))];

  const getPrediction = (dept: string, stage: string) =>
    data.find((p) => p.department === dept && p.stage === stage);

  const highRiskCount = data.filter((p) => p.breachProbability >= 0.5).length;
  const criticalRiskCount = data.filter((p) => p.breachProbability >= 0.8).length;

  return (
    <div>
      {/* ── Summary bar ──────────────────────────────────────── */}
      <div className="flex items-center gap-3 mb-3 text-xs">
        <span className="text-gray-500 dark:text-gray-400">
          {data.length} cells · {departments.length} departments · {stages.length} stages
        </span>
        {highRiskCount > 0 && (
          <span className="px-2 py-0.5 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 font-medium">
            {highRiskCount} high risk
          </span>
        )}
        {criticalRiskCount > 0 && (
          <span className="px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-medium">
            {criticalRiskCount} critical
          </span>
        )}
      </div>

      {/* ── Heatmap grid ─────────────────────────────────────── */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="text-left text-gray-500 dark:text-gray-400 font-medium pb-2 pr-3">
                Department
              </th>
              {stages.map((stage) => (
                <th
                  key={stage}
                  className="text-center text-gray-500 dark:text-gray-400 font-medium pb-2 px-2 min-w-[80px]"
                >
                  {stage}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {departments.map((dept) => (
              <tr key={dept}>
                <td className="text-navy-900 dark:text-white font-medium py-1.5 pr-3 whitespace-nowrap">
                  {dept}
                </td>
                {stages.map((stage) => {
                  const pred = getPrediction(dept, stage);
                  const prob = pred?.breachProbability ?? 0;
                  const pct = Math.round(prob * 100);

                  return (
                    <td key={stage} className="p-1">
                      <button
                        onClick={() => pred && setSelectedCell(pred)}
                        className={`w-full h-10 rounded-lg border ${getHeatColor(prob)} ${getHeatIntensity(prob)} flex flex-col items-center justify-center cursor-pointer hover:opacity-80 transition-opacity`}
                        title={`${dept} - ${stage}: ${pct}% breach risk`}
                      >
                        <span className="text-xs font-bold leading-tight">{pct}%</span>
                        {pred && (
                          <span className="text-[10px] opacity-70 leading-tight">
                            {pred.affectedReviewCount} reviews
                          </span>
                        )}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Legend ────────────────────────────────────────────── */}
      <div className="flex items-center gap-4 mt-3 text-[10px] text-gray-500 dark:text-gray-400">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-green-100 border border-green-200" /> &lt;20%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-yellow-100 border border-yellow-200" /> 20-50%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-orange-100 border border-orange-200" /> 50-80%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-red-100 border border-red-200" /> &gt;80%
        </span>
      </div>

      {/* ── Cell drill-down modal ─────────────────────────────── */}
      {selectedCell && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl max-w-sm w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-navy-900 dark:text-white">
                {selectedCell.department} — {selectedCell.stage}
              </h3>
              <button
                onClick={() => setSelectedCell(null)}
                className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Breach Probability</span>
                <span className="font-semibold text-navy-900 dark:text-white">
                  {Math.round(selectedCell.breachProbability * 100)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Affected Reviews</span>
                <span className="font-semibold text-navy-900 dark:text-white">
                  {selectedCell.affectedReviewCount}
                </span>
              </div>
              <div className="w-full h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden mt-1">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${selectedCell.breachProbability * 100}%`,
                    backgroundColor: getHeatColor(selectedCell.breachProbability).includes("red")
                      ? "#EF4444"
                      : getHeatColor(selectedCell.breachProbability).includes("orange")
                      ? "#F97316"
                      : getHeatColor(selectedCell.breachProbability).includes("yellow")
                      ? "#EAB308"
                      : "#10B981",
                  }}
                />
              </div>
            </div>
            <button
              onClick={() => setSelectedCell(null)}
              className="mt-4 w-full py-2 text-xs font-medium rounded-lg bg-navy-900 dark:bg-navy-600 text-white hover:bg-navy-800 transition-colors"
            >
              View Affected Reviews
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

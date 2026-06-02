/**
 * TenantHealthWidget — Composite health score with dimension breakdown.
 *
 * Displays a gauge-style composite score (0-1) with 6 dimension sparklines:
 * - SLA adherence
 * - Backlog depth
 * - Escalation rate
 * - Delivery velocity
 * - Replay health
 * - Worker pool status
 *
 * Includes drill-down modal showing dimension history (7d/30d/90d).
 */

"use client";

import React, { useState } from "react";
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from "recharts";

interface HealthDimension {
  label: string;
  value: number; // 0-1
  trend: "up" | "down" | "stable";
  history?: number[];
}

interface HealthScoreData {
  composite: number;
  dimensions: HealthDimension[];
  status: "healthy" | "degraded" | "unhealthy";
}

interface TenantHealthWidgetProps {
  healthScore?: HealthScoreData | null;
}

function getStatusColor(score: number): string {
  if (score == null || isNaN(score)) return "#6B7280"; // gray for no data
  if (score >= 0.8) return "#10B981"; // green
  if (score >= 0.5) return "#F59E0B"; // amber
  return "#EF4444"; // red
}

function getStatusLabel(score: number): string {
  if (score == null || isNaN(score)) return "No Data";
  if (score >= 0.8) return "Healthy";
  if (score >= 0.5) return "Degraded";
  return "Unhealthy";
}

function TrendIcon({ trend }: { trend: "up" | "down" | "stable" }) {
  if (trend === "up") {
    return <span className="text-green-600 dark:text-green-400 text-xs">↑</span>;
  }
  if (trend === "down") {
    return <span className="text-red-600 dark:text-red-400 text-xs">↓</span>;
  }
  return <span className="text-gray-400 text-xs">→</span>;
}

export function TenantHealthWidget({ healthScore }: TenantHealthWidgetProps) {
  const [showDrilldown, setShowDrilldown] = useState(false);

  // No data state — show empty state instead of fake metrics
  if (!healthScore) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-navy-700 flex items-center justify-center mb-2">
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No health data available</p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Connect to the backend to see tenant health metrics.</p>
      </div>
    );
  }

  const data = healthScore;

  const color = getStatusColor(data.composite);
  const displayPercent = data.composite != null && !isNaN(data.composite)
    ? Math.round(data.composite * 100)
    : "—";

  return (
    <>
      <div className="flex items-start gap-4">
        {/* ── Gauge ──────────────────────────────────────────── */}
        <div className="w-24 h-24 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="70%"
              outerRadius="100%"
              barSize={12}
              data={[{ name: "health", value: data.composite * 100, fill: color }]}
              startAngle={180}
              endAngle={0}
            >
              <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
              <RadialBar
                background
                dataKey="value"
                cornerRadius={6}
                fill={color}
              />
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-lg font-bold"
                fill={color}
              >
                {displayPercent}{typeof displayPercent === "number" ? "%" : ""}
              </text>
            </RadialBarChart>
          </ResponsiveContainer>
        </div>

        {/* ── Dimensions ─────────────────────────────────────── */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-navy-900 dark:text-white uppercase tracking-wider">
              Composite Health
            </span>
            <div className="flex items-center gap-1.5">
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{
                  backgroundColor: `${color}20`,
                  color: color,
                }}
              >
                {getStatusLabel(data.composite)}
              </span>
            </div>
          </div>
          <div className="space-y-1.5">
            {data.dimensions.map((dim) => (
              <div key={dim.label} className="flex items-center gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400 truncate">
                      {dim.label}
                    </span>
                    <span className="flex items-center gap-1 text-navy-900 dark:text-white font-medium">
                      {dim.value != null && !isNaN(dim.value) ? `${Math.round(dim.value * 100)}%` : "—"} <TrendIcon trend={dim.trend} />
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full mt-0.5 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: dim.value != null && !isNaN(dim.value) ? `${dim.value * 100}%` : "0%",
                        backgroundColor: getStatusColor(dim.value),
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Drill-down button ────────────────────────────────── */}
      <button
        onClick={() => setShowDrilldown(true)}
        className="mt-3 w-full text-xs text-center text-gray-500 dark:text-gray-400 hover:text-navy-700 dark:hover:text-navy-200 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
      >
        View dimension history →
      </button>

      {/* ── Drill-down Modal ─────────────────────────────────── */}
      {showDrilldown && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-navy-900 dark:text-white">
                Health Dimension History
              </h3>
              <button
                onClick={() => setShowDrilldown(false)}
                className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="space-y-4">
              {data.dimensions.map((dim) => (
                <div key={dim.label} className="p-3 bg-gray-50 dark:bg-navy-700 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-navy-900 dark:text-white">{dim.label}</span>
                    <span className="text-xs text-gray-500">{dim.value != null && !isNaN(dim.value) ? `${Math.round(dim.value * 100)}%` : "—"}</span>
                  </div>
                  {/* Mini sparkline placeholder */}
                  <div className="h-8 bg-gray-200 dark:bg-navy-600 rounded flex items-center justify-center">
                    <span className="text-[10px] text-gray-400">7d trend chart</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

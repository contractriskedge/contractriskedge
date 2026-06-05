/**
 * BenchmarkAnalyticsWidget — Cycle Time vs Benchmark, SLA vs Benchmark,
 * Reviewer Efficiency vs Benchmark.
 *
 * Shows how current operational metrics compare against industry/target benchmarks.
 * Data sourced from executive aggregation layer — no hardcoded defaults.
 */

"use client";

import React from "react";
import type { BenchmarkAnalyticsData } from "@/src/lib/executive/executiveTypes";

interface BenchmarkAnalyticsWidgetProps {
  benchmark?: BenchmarkAnalyticsData | null;
}

const BENCHMARK_META: Record<string, { label: string; unit: string; higherIsBetter: boolean; benchmarkLabel: string }> = {
  cycle_time: { label: "Cycle Time", unit: "days", higherIsBetter: false, benchmarkLabel: "Target" },
  sla: { label: "SLA Compliance", unit: "%", higherIsBetter: true, benchmarkLabel: "Target" },
  reviewer_load: { label: "Reviewer Efficiency", unit: "load", higherIsBetter: false, benchmarkLabel: "Max Load" },
};

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ahead: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300",
    on_track: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300",
    behind: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300",
    no_data: "bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400",
  };
  const labels: Record<string, string> = {
    ahead: "Ahead",
    on_track: "On Track",
    behind: "Behind",
    no_data: "N/A",
  };
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${colors[status] ?? "bg-gray-100 text-gray-600"}`}>
      {labels[status] ?? status}
    </span>
  );
}

export function BenchmarkAnalyticsWidget({ benchmark }: BenchmarkAnalyticsWidgetProps) {
  if (!benchmark) {
    return (
      <div className="flex items-center justify-center h-32 text-xs text-gray-400">
        No benchmark data available
      </div>
    );
  }

  const items = [
    {
      key: "cycle_time",
      status: benchmark.cycle_time_vs_benchmark,
      current: `${benchmark.current_cycle_time_days.toFixed(1)}d`,
      benchmark: `${benchmark.benchmark_cycle_time_days}d target`,
      actual: benchmark.current_cycle_time_days,
      target: benchmark.benchmark_cycle_time_days,
    },
    {
      key: "sla",
      status: benchmark.sla_vs_benchmark,
      current: `${benchmark.current_sla_pct.toFixed(1)}%`,
      benchmark: `${benchmark.benchmark_sla_pct}% target`,
      actual: benchmark.current_sla_pct,
      target: benchmark.benchmark_sla_pct,
    },
    {
      key: "reviewer_load",
      status: benchmark.reviewer_efficiency_vs_benchmark,
      current: `${benchmark.current_reviewer_load.toFixed(1)}`,
      benchmark: `max ${benchmark.benchmark_reviewer_load}`,
      actual: benchmark.current_reviewer_load,
      target: benchmark.benchmark_reviewer_load,
    },
  ];

  return (
    <div className="space-y-3">
      {/* ── Three Benchmark Cards ── */}
      <div className="grid grid-cols-3 gap-2">
        {items.map((item) => {
          const meta = BENCHMARK_META[item.key];
          return (
            <div key={item.key} className="p-2.5 rounded-lg bg-gray-50 dark:bg-navy-700">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase font-medium">
                  {meta?.label ?? item.key}
                </span>
                <StatusBadge status={item.status} />
              </div>
              <p className="text-base font-bold text-navy-900 dark:text-white">
                {item.current}
              </p>
              <p className="text-[10px] text-gray-400 mt-0.5">
                {meta?.benchmarkLabel ?? "Benchmark"}: {item.benchmark}
              </p>
            </div>
          );
        })}
      </div>

      {/* ── Benchmark Comparison Bars ── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1.5 block">
          Performance vs Target
        </span>
        <div className="space-y-2">
          {items.map((item) => {
            const meta = BENCHMARK_META[item.key];
            if (item.status === "no_data") {
              return (
                <div key={item.key} className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-500 dark:text-gray-400 w-20 truncate" title={meta?.label}>
                    {meta?.label ?? item.key}
                  </span>
                  <div className="flex-1 h-2.5 bg-gray-100 dark:bg-navy-700 rounded-full flex items-center justify-center">
                    <span className="text-[9px] text-gray-400">—</span>
                  </div>
                  <span className="text-[10px] font-medium w-10 text-right text-gray-400">N/A</span>
                </div>
              );
            }
            const pct = item.target > 0 ? Math.min(100, (item.actual / item.target) * 100) : 0;
            const isGood = meta?.higherIsBetter ? pct >= 100 : pct <= 100;
            return (
              <div key={item.key} className="flex items-center gap-2 group">
                <span className="text-[10px] text-gray-500 dark:text-gray-400 w-20 truncate" title={meta?.label}>
                  {meta?.label ?? item.key}
                </span>
                <div className="flex-1 h-2.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden relative">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(pct, 100)}%`,
                      backgroundColor: isGood ? "#10B981" : "#EF4444",
                    }}
                  />
                </div>
                <span className={`text-[10px] font-medium w-10 text-right ${isGood ? "text-green-600" : "text-red-600"}`}>
                  {item.status === "ahead" ? "✓" : item.status === "behind" ? "!" : "~"}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Legend ── */}
      <div className="flex items-center gap-3 text-[10px] text-gray-400 pt-1 border-t border-gray-100 dark:border-navy-700">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500" /> Ahead
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-500" /> On Track
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-500" /> Behind
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-gray-300" /> No Data
        </span>
      </div>
    </div>
  );
}

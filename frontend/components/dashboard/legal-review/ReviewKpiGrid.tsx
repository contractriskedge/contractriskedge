"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, ArrowDownRight, TrendingUp, ShieldCheck, Clock3, Users, Sparkles, Activity } from "lucide-react";
import type { KpiMetric } from "./types";

const severityStyles: Record<string, string> = {
  critical: "text-red-700 bg-red-50 border-red-200",
  high: "text-orange-700 bg-orange-50 border-orange-200",
  medium: "text-yellow-700 bg-yellow-50 border-yellow-200",
  low: "text-green-700 bg-green-50 border-green-200",
  normal: "text-slate-700 bg-slate-50 border-slate-200",
};

function TrendLabel({ trend }: { trend: number }) {
  const Icon = trend >= 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${trend >= 0 ? "text-green-700" : "text-red-700"}`}>
      <Icon className="w-3.5 h-3.5" aria-hidden="true" />
      {Math.abs(trend)}%
    </span>
  );
}

export function ReviewKpiGrid({ metrics }: { metrics: KpiMetric[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <motion.article
            key={metric.key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="group rounded-3xl border border-slate-200/70 bg-white/90 p-5 shadow-sm shadow-slate-200/20 transition hover:-translate-y-0.5 hover:shadow-md hover:shadow-slate-300/20 dark:border-navy-700 dark:bg-navy-900 dark:shadow-black/10"
            role="region"
            aria-labelledby={`kpi-${metric.key}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p id={`kpi-${metric.key}`} className="text-sm font-semibold text-slate-900 dark:text-white">
                  {metric.label}
                </p>
                <p className="mt-3 text-3xl font-bold tracking-tight text-navy-900 dark:text-white">
                  {metric.value}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-slate-700 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-200">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </div>
            </div>

            <div className="mt-5 flex items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
              <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 ${severityStyles[metric.severity]}`}>
                {metric.severity.replace(/-/g, " ")}
              </span>
              <TrendLabel trend={metric.trend} />
            </div>

            <div className="mt-4 h-12 overflow-hidden rounded-2xl bg-slate-100 dark:bg-navy-800">
              <div className="relative h-full flex items-end gap-1 px-2 py-2">
                {metric.sparkline.map((value, index) => (
                  <div
                    key={index}
                    className="h-full w-2 rounded-full bg-gradient-to-t from-slate-800 to-slate-500 dark:from-slate-300 dark:to-slate-100 transition-all"
                    style={{ height: `${Math.max(value, 8)}%` }}
                  />
                ))}
              </div>
            </div>

            <button
              type="button"
              className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
            >
              View details
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </motion.article>
        );
      })}
    </div>
  );
}

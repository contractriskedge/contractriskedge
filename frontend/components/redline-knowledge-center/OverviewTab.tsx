/**
 * Overview tab — summary cards + quick actions.
 */
"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  TrendingUp,
  ArrowUp,
  Loader2,
} from "lucide-react";
import { useCoverage, useMissingTemplates } from "@/services/hooks/useRedlineTemplates";

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {value}
          </p>
          {sub && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{sub}</p>
          )}
        </div>
        <div className={`p-2.5 rounded-lg ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </motion.div>
  );
}

export function OverviewTab() {
  const { data: coverage, isLoading } = useCoverage();
  const { data: missing } = useMissingTemplates(5);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
      </div>
    );
  }

  const stats = [
    {
      icon: FileText,
      label: "Total Findings",
      value: coverage?.total_findings ?? 0,
      sub: "Across all contracts",
      color: "bg-blue-500",
    },
    {
      icon: CheckCircle2,
      label: "Templates Available",
      value: coverage?.total_templates ?? 0,
      sub: `${coverage?.templates_used ?? 0} findings covered`,
      color: "bg-emerald-500",
    },
    {
      icon: AlertTriangle,
      label: "Missing Templates",
      value: coverage?.templates_missing ?? 0,
      sub: `${coverage?.coverage_pct ?? 0}% coverage`,
      color: "bg-amber-500",
    },
    {
      icon: TrendingUp,
      label: "Coverage Rate",
      value: `${coverage?.coverage_pct ?? 0}%`,
      sub: "Of findings have templates",
      color: "bg-indigo-500",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <StatCard key={i} {...stat} />
        ))}
      </div>

      {/* Missing Templates Preview */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-500" />
            Top Missing Templates
          </h3>
          <span className="text-xs text-gray-400">
            Generate drafts for these clause types
          </span>
        </div>
        <div className="space-y-2">
          {(missing ?? []).slice(0, 5).map((item) => (
            <div
              key={item.clause_type}
              className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
            >
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                  {item.clause_type.replace(/_/g, " ")}
                </p>
                <p className="text-xs text-gray-400">
                  {item.findings} findings
                </p>
              </div>
              <button className="text-xs px-3 py-1.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-md hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors">
                Generate Draft
              </button>
            </div>
          ))}
          {(!missing || missing.length === 0) && (
            <p className="text-sm text-gray-400 text-center py-4">
              No missing templates — all findings are covered!
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

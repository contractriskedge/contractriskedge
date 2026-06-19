/**
 * Analytics tab — template usage stats, coverage trends, and adoption metrics.
 */
"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart,
  Loader2,
} from "lucide-react";
import { useCoverage } from "@/services/hooks/useRedlineTemplates";

export function AnalyticsTab() {
  const { data: coverage, isLoading } = useCoverage();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
      </div>
    );
  }

  const covered = coverage?.by_clause_type?.filter((c) => c.status === "covered").length ?? 0;
  const partial = coverage?.by_clause_type?.filter((c) => c.status === "partial").length ?? 0;
  const missing = coverage?.by_clause_type?.filter((c) => c.status === "missing").length ?? 0;
  const total = covered + partial + missing;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Coverage Pie */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-indigo-500" />
            Coverage Breakdown
          </h3>
          <div className="flex items-center justify-center">
            <div className="relative w-32 h-32">
              <svg viewBox="0 0 36 36" className="w-full h-full">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="3"
                  className="dark:stroke-gray-700"
                />
                {covered > 0 && (
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="3"
                    strokeDasharray={`${(covered / Math.max(total, 1)) * 100} ${100 - (covered / Math.max(total, 1)) * 100}`}
                    strokeDashoffset="0"
                  />
                )}
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {coverage?.coverage_pct ?? 0}%
                </span>
              </div>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Covered
              </span>
              <span className="font-medium text-gray-900 dark:text-white">{covered}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                Partial
              </span>
              <span className="font-medium text-gray-900 dark:text-white">{partial}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                Missing
              </span>
              <span className="font-medium text-gray-900 dark:text-white">{missing}</span>
            </div>
          </div>
        </div>

        {/* Usage Stats */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-indigo-500" />
            Template Usage
          </h3>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Findings</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {coverage?.total_findings ?? 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Findings Covered</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {coverage?.templates_used ?? 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Findings Missing</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {coverage?.templates_missing ?? 0}
              </p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button className="w-full text-left px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors">
              <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
                Generate Missing Templates
              </p>
              <p className="text-xs text-indigo-400 dark:text-indigo-500 mt-0.5">
                {missing} clause types need templates
              </p>
            </button>
            <button className="w-full text-left px-4 py-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors">
              <p className="text-sm font-medium text-purple-600 dark:text-purple-400">
                Batch AI Generation
              </p>
              <p className="text-xs text-purple-400 dark:text-purple-500 mt-0.5">
                Generate all missing drafts at once
              </p>
            </button>
            <button className="w-full text-left px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/30 transition-colors">
              <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                Export Coverage Report
              </p>
              <p className="text-xs text-emerald-400 dark:text-emerald-500 mt-0.5">
                Download as CSV or PDF
              </p>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

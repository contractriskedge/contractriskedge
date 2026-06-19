/**
 * Coverage tab — per-clause-type coverage table with actions.
 */
"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  FilePlus2,
  Search,
  Download,
} from "lucide-react";
import { useCoverage, useGenerateDraft } from "@/services/hooks/useRedlineTemplates";
import type { CoverageItem } from "@/services/api/redlineTemplates";

const STATUS_BADGE = {
  covered: { label: "Covered", class: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" },
  partial: { label: "Partial", class: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
  missing: { label: "Missing", class: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
} as const;

export function CoverageTab() {
  const { data: coverage, isLoading } = useCoverage();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const generateDraft = useGenerateDraft();
  const [generating, setGenerating] = useState<string | null>(null);

  const filtered = (coverage?.by_clause_type ?? []).filter((item) => {
    const matchesSearch = item.clause_type.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || item.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleGenerate = async (item: CoverageItem) => {
    setGenerating(item.clause_type);
    try {
      await generateDraft.mutateAsync({
        clause_type: item.clause_type,
        finding_title: `Missing ${item.clause_type.replace(/_/g, " ")} Clause`,
        finding_description: `${item.total_findings} findings detected across regression suite`,
      });
      alert(`Draft generated for ${item.clause_type}! Check AI Suggestions tab.`);
    } catch {
      alert("Failed to generate draft. Check API key and try again.");
    } finally {
      setGenerating(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Bar */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-4 border border-emerald-200 dark:border-emerald-800">
          <p className="text-sm text-emerald-600 dark:text-emerald-400">Covered</p>
          <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">
            {coverage?.by_clause_type?.filter((c) => c.status === "covered").length ?? 0}
          </p>
        </div>
        <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
          <p className="text-sm text-amber-600 dark:text-amber-400">Partial</p>
          <p className="text-2xl font-bold text-amber-700 dark:text-amber-300">
            {coverage?.by_clause_type?.filter((c) => c.status === "partial").length ?? 0}
          </p>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">Missing</p>
          <p className="text-2xl font-bold text-red-700 dark:text-red-300">
            {coverage?.by_clause_type?.filter((c) => c.status === "missing").length ?? 0}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search clause types..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
        >
          <option value="all">All Status</option>
          <option value="covered">Covered</option>
          <option value="partial">Partial</option>
          <option value="missing">Missing</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Clause Type</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Findings</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Templates</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Active</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Coverage</th>
                <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Status</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {filtered.map((item) => {
                const badge = STATUS_BADGE[item.status];
                return (
                  <motion.tr
                    key={item.clause_type}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white capitalize">
                      {item.clause_type.replace(/_/g, " ")}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                      {item.total_findings}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                      {item.templates_available}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                      {item.active_templates}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-medium ${
                        item.coverage_pct >= 50 ? "text-emerald-600" : item.coverage_pct > 0 ? "text-amber-600" : "text-red-600"
                      }`}>
                        {item.coverage_pct}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${badge.class}`}>
                        {item.status === "covered" ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {item.status === "missing" ? (
                        <button
                          onClick={() => handleGenerate(item)}
                          disabled={generating === item.clause_type}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-md hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors disabled:opacity-50"
                        >
                          {generating === item.clause_type ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <FilePlus2 className="w-3 h-3" />
                          )}
                          Generate
                        </button>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                  </motion.tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-gray-400">
                    No clause types match your filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

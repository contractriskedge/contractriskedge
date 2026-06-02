/**
 * PolicyIssuesSection — Policy violations, missing clauses, compliance impact.
 *
 * Shows:
 * - Open policy violations with severity
 * - Missing mandatory clauses
 * - Expected vs actual comparison
 * - Compliance impact assessment
 * - Waive actions
 */

"use client";

import React, { useState, useMemo } from "react";
import {
  Shield, AlertTriangle, CheckCircle2, XCircle, Gavel,
  BookOpen, Lightbulb, Search, ChevronDown, ChevronUp, Loader2,
  ExternalLink,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";

export function PolicyIssuesSection() {
  const ctx = useReviewContext();
  const { policyViolations, missingClauses } = ctx;

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showMissing, setShowMissing] = useState(true);

  const violations = policyViolations ?? [];
  const missing = missingClauses ?? [];

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return violations;
    const q = searchQuery.toLowerCase();
    return violations.filter(v =>
      v.policy_name.toLowerCase().includes(q) ||
      v.clause_type.toLowerCase().includes(q) ||
      v.description.toLowerCase().includes(q)
    );
  }, [violations, searchQuery]);

  const openViolations = violations.filter(v => v.status === "open").length;

  return (
    <div className="p-4 space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Open Violations", value: openViolations, color: openViolations > 0 ? "text-red-600" : "text-green-600" },
          { label: "Waived", value: violations.filter(v => v.status === "waived").length, color: "text-gray-500" },
          { label: "Missing Clauses", value: missing.length, color: missing.length > 0 ? "text-amber-600" : "text-green-600" },
        ].map(s => (
          <div key={s.label} className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3 text-center">
            <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
            <div className="text-[9px] text-gray-500 uppercase">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
        <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search violations..." className="w-full pl-7 pr-2 py-1.5 text-[11px] bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400" />
      </div>

      {/* Missing Clauses */}
      {showMissing && missing.length > 0 && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/10 overflow-hidden">
          <button onClick={() => setShowMissing(!showMissing)} className="w-full flex items-center justify-between px-3 py-2 bg-amber-100 dark:bg-amber-900/20">
            <span className="text-[10px] font-semibold text-amber-700 dark:text-amber-300">Missing Clauses ({missing.length})</span>
            {showMissing ? <ChevronUp className="w-3 h-3 text-amber-500" /> : <ChevronDown className="w-3 h-3 text-amber-500" />}
          </button>
          {showMissing && (
            <div className="divide-y divide-amber-100 dark:divide-amber-800">
              {missing.map(mc => (
                <div key={mc.id} className="px-3 py-2">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <XCircle className="w-3 h-3 text-red-400 flex-shrink-0" />
                    <span className="text-[10px] font-semibold text-navy-900 dark:text-white">{mc.clause_type}</span>
                    <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
                      mc.importance === "required" ? "bg-red-100 text-red-700" :
                      mc.importance === "recommended" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600"
                    }`}>{mc.importance}</span>
                  </div>
                  <p className="text-[9px] text-gray-500 ml-4.5">{mc.reason}</p>
                  <div className="ml-4.5 mt-1 flex items-start gap-1 p-1.5 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
                    <Lightbulb className="w-2.5 h-2.5 text-amber-500 mt-0.5 flex-shrink-0" />
                    <span className="text-[8px] text-gray-600 dark:text-gray-400">{mc.fallback_recommendation}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Violations List */}
      <div className="space-y-1.5">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Shield className="w-8 h-8 text-green-300 dark:text-green-600 mb-2" />
            <p className="text-xs text-gray-500">No policy violations found</p>
          </div>
        ) : filtered.map(v => {
          const isExpanded = expandedId === v.id;
          return (
            <div key={v.id} className={`rounded-lg border overflow-hidden transition-shadow hover:shadow-sm ${
              v.severity === "critical" ? "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10" :
              v.severity === "high" ? "border-red-100 dark:border-red-800 bg-red-50/50 dark:bg-red-900/5" :
              "border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/10"
            }`}>
              <button onClick={() => setExpandedId(isExpanded ? null : v.id)} className="w-full flex items-start gap-2 px-3 py-2 text-left">
                <Gavel className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`text-[10px] font-semibold ${
                      v.severity === "critical" ? "text-red-700" :
                      v.severity === "high" ? "text-red-600" : "text-amber-700"
                    }`}>{v.policy_name}</span>
                    <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
                      v.compliance_impact === "critical" ? "bg-red-100 text-red-700" :
                      v.compliance_impact === "high" ? "bg-orange-100 text-orange-700" : "bg-amber-100 text-amber-700"
                    }`}>{v.compliance_impact}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[8px] text-gray-500">
                    <span>{v.clause_type}</span>
                    <span>·</span>
                    <span>{v.regulation}</span>
                    <span>·</span>
                    <span>p.{v.page_number}</span>
                  </div>
                </div>
                {isExpanded ? <ChevronUp className="w-3 h-3 text-gray-400" /> : <ChevronDown className="w-3 h-3 text-gray-400" />}
              </button>
              {isExpanded && (
                <div className="px-3 pb-2.5 space-y-1.5 border-t border-gray-100 dark:border-navy-700 pt-1.5">
                  <p className="text-[9px] text-gray-700 dark:text-gray-300">{v.description}</p>
                  <div className="grid grid-cols-2 gap-1.5">
                    <div className="p-1.5 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
                      <span className="text-[7px] font-semibold text-green-700 uppercase">Expected</span>
                      <p className="text-[8px] text-gray-600 mt-0.5">{v.expected}</p>
                    </div>
                    <div className="p-1.5 rounded bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800">
                      <span className="text-[7px] font-semibold text-red-700 uppercase">Actual</span>
                      <p className="text-[8px] text-gray-600 mt-0.5">{v.actual}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-1 p-1.5 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
                    <Lightbulb className="w-2.5 h-2.5 text-amber-500 mt-0.5 flex-shrink-0" />
                    <span className="text-[8px] text-gray-600 dark:text-gray-400">{v.recommendation}</span>
                  </div>
                  {/* Locate Evidence */}
                  <div className="flex items-center gap-2 pt-0.5">
                    <button onClick={() => {
                      import("@/lib/highlightClause").then(({ locateClause }) => {
                        locateClause({ page: v.page_number || 1, findingId: v.id, clauseText: v.actual });
                      });
                    }}
                      className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-cyan-100 text-cyan-700 hover:bg-cyan-200 border border-cyan-200 transition-colors">
                      <ExternalLink className="w-2.5 h-2.5" /> Locate Evidence
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

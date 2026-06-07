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
  ExternalLink, ShieldCheck,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useReviewContext } from "./ReviewContext";
import { reviewService } from "@/services/api/reviews";

export function PolicyIssuesSection() {
  const ctx = useReviewContext();
  const { policyViolations, missingClauses, selectedReviewId } = ctx;
  const queryClient = useQueryClient();

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showMissing, setShowMissing] = useState(true);
  const [waivingId, setWaivingId] = useState<string | null>(null);
  const [waiveJustification, setWaiveJustification] = useState("");
  const [waiveError, setWaiveError] = useState<string | null>(null);
  const [waiving, setWaiving] = useState(false);
  const [waivedIds, setWaivedIds] = useState<Set<string>>(new Set());
  const [waiveToast, setWaiveToast] = useState<string | null>(null);

  const violations = policyViolations ?? [];
  const missing = missingClauses ?? [];

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return violations;
    const q = searchQuery.toLowerCase();
    return violations.filter(v =>
      (v.policy_name || "").toLowerCase().includes(q) ||
      (v.clause_type || "").toLowerCase().includes(q) ||
      (v.finding_title || v.description || "").toLowerCase().includes(q)
    );
  }, [violations, searchQuery]);

  const openViolations = violations.filter(
    v => v.status === "open" && !waivedIds.has(v.rule_id ?? "")
  ).length;

  const submitWaive = async (ruleId: string) => {
    if (!selectedReviewId) return;
    if (!waiveJustification.trim()) {
      setWaiveError("Justification is required");
      return;
    }
    setWaiving(true);
    setWaiveError(null);
    try {
      await reviewService.waivePolicyViolation(selectedReviewId, {
        rule_id: ruleId,
        justification: waiveJustification,
      });
      // Re-fetch policy violations so the new "waiver pending" status
      // surfaces from the backend on the next render.
      queryClient.invalidateQueries({ queryKey: ["reviews", "policy", selectedReviewId] });
      queryClient.invalidateQueries({ queryKey: ["ai-platform"] });
      // Optimistically mark the rule as waived in the local UI set so the
      // user sees immediate feedback.
      setWaivedIds(prev => new Set(prev).add(ruleId));
      setWaivingId(null);
      setWaiveJustification("");
      setWaiveToast(`Waiver submitted for review.`);
      window.setTimeout(() => setWaiveToast(null), 3000);
    } catch (err) {
      setWaiveError(err instanceof Error ? err.message : "Waiver failed");
    } finally {
      setWaiving(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      {/* Waive toast */}
      {waiveToast && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-green-200 bg-green-50 text-[10px] text-green-800 dark:border-green-800 dark:bg-green-900/20 dark:text-green-200">
          <CheckCircle2 className="w-3 h-3" />
          {waiveToast}
        </div>
      )}
      {/* Stats */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: "Open", value: openViolations, color: openViolations > 0 ? "text-red-600" : "text-green-600" },
          { label: "Waived", value: violations.filter(v => v.status === "waived" || waivedIds.has(v.rule_id ?? "")).length, color: "text-gray-500" },
          { label: "Rules", value: violations.length, color: "text-blue-600" },
          { label: "Missing", value: missing.length, color: missing.length > 0 ? "text-amber-600" : "text-green-600" },
        ].map(s => (
          <div key={s.label} className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-2 text-center">
            <div className={`text-base font-bold ${s.color}`}>{s.value}</div>
            <div className="text-[8px] text-gray-500 uppercase">{s.label}</div>
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
                  <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                    <span className={`text-[10px] font-semibold ${
                      v.severity === "critical" ? "text-red-700" :
                      v.severity === "high" ? "text-red-600" : "text-amber-700"
                    }`}>{v.policy_name || "Policy Rule"}</span>
                    <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
                      v.severity === "critical" ? "bg-red-100 text-red-700" :
                      v.severity === "high" ? "bg-orange-100 text-orange-700" : "bg-amber-100 text-amber-700"
                    }`}>{v.severity || "medium"}</span>
                    {v.is_mandatory && (
                      <span className="text-[8px] px-1 py-0.5 rounded font-medium bg-red-100 text-red-700">
                        Mandatory
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-[8px] text-gray-500 flex-wrap">
                    {v.clause_type && <span className="font-medium">{v.clause_type}</span>}
                    {v.finding_title && (
                      <>
                        <span>·</span>
                        <span className="truncate max-w-[200px]" title={v.finding_title}>{v.finding_title}</span>
                      </>
                    )}
                    {v.effect && (
                      <>
                        <span>·</span>
                        <span className="text-blue-600">{v.effect}</span>
                      </>
                    )}
                  </div>
                </div>
                {isExpanded ? <ChevronUp className="w-3 h-3 text-gray-400" /> : <ChevronDown className="w-3 h-3 text-gray-400" />}
              </button>
              {isExpanded && (
                <div className="px-3 pb-2.5 space-y-1.5 border-t border-gray-100 dark:border-navy-700 pt-1.5">
                  {v.finding_description && (
                    <p className="text-[9px] text-gray-700 dark:text-gray-300">{v.finding_description}</p>
                  )}
                  <div className="grid grid-cols-2 gap-1.5">
                    <div className="p-1.5 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
                      <span className="text-[7px] font-semibold text-green-700 uppercase">Policy Rule</span>
                      <p className="text-[8px] text-gray-600 mt-0.5">{v.rule_description || v.policy_name || "—"}</p>
                    </div>
                    <div className="p-1.5 rounded bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800">
                      <span className="text-[7px] font-semibold text-red-700 uppercase">Finding</span>
                      <p className="text-[8px] text-gray-600 mt-0.5">{v.finding_title || "—"}</p>
                    </div>
                  </div>
                  {v.recommendation && (
                    <div className="flex items-start gap-1 p-1.5 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
                      <Lightbulb className="w-2.5 h-2.5 text-amber-500 mt-0.5 flex-shrink-0" />
                      <span className="text-[8px] text-gray-600 dark:text-gray-400">{v.recommendation}</span>
                    </div>
                  )}
                  {/* Finding Cross-Reference */}
                  {v.finding_id && (() => {
                    const linkedFinding = ctx.findings?.find(f => f.finding_id === v.finding_id);
                    return (
                      <div className="flex items-center gap-1.5 p-1.5 rounded bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-200 dark:border-indigo-800">
                        <ExternalLink className="w-2.5 h-2.5 text-indigo-500 flex-shrink-0" />
                        <span className="text-[8px] text-indigo-700 dark:text-indigo-300">
                          Linked Finding: <strong>{linkedFinding?.title || v.finding_id.slice(0, 8)}</strong>
                        </span>
                        {linkedFinding && (
                          <span className={`ml-auto text-[7px] font-medium px-1.5 py-0.5 rounded-full ${
                            linkedFinding.severity === 'critical' ? 'bg-red-100 text-red-700' :
                            linkedFinding.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                            'bg-amber-100 text-amber-700'
                          }`}>{linkedFinding.severity}</span>
                        )}
                        <button onClick={() => ctx.setActiveSection('findings')}
                          className="ml-1 px-1.5 py-0.5 text-[7px] font-medium rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200">
                          View
                        </button>
                      </div>
                    );
                  })()}
                  {/* Locate Evidence + Waive */}
                  <div className="flex items-center gap-2 pt-0.5 flex-wrap">
                    {v.finding_id && (
                      <button onClick={() => {
                        import("@/lib/highlightClause").then(({ locateClause }) => {
                          locateClause({ page: 1, findingId: v.finding_id || "", clauseText: v.finding_title || v.finding_description || "" });
                        });
                      }}
                        className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-cyan-100 text-cyan-700 hover:bg-cyan-200 border border-cyan-200 transition-colors">
                        <ExternalLink className="w-2.5 h-2.5" /> Locate Finding
                      </button>
                    )}
                    {v.status === "open" && v.rule_id && !waivedIds.has(v.rule_id) && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setWaivingId(waivingId === v.id ? null : v.id); setWaiveError(null); }}
                        className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-amber-100 text-amber-700 hover:bg-amber-200 border border-amber-200 transition-colors">
                        <ShieldCheck className="w-2.5 h-2.5" />
                        {waivingId === v.id ? "Cancel" : "Waive"}
                      </button>
                    )}
                    {(v.status === "waived" || waivedIds.has(v.rule_id ?? "")) && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-gray-100 text-gray-600 border border-gray-200">
                        <CheckCircle2 className="w-2.5 h-2.5 text-green-600" /> Waived
                      </span>
                    )}
                    {v.waiver_status === "pending" && !waivedIds.has(v.rule_id ?? "") && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-amber-50 text-amber-700 border border-amber-200">
                        Waiver pending
                      </span>
                    )}
                  </div>
                  {/* Inline waiver form */}
                  {waivingId === v.id && v.rule_id && (
                    <div className="mt-1.5 p-2 rounded border border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-900/10 space-y-1.5">
                      <label className="text-[8px] font-semibold text-amber-800 dark:text-amber-300 uppercase">
                        Waiver Justification (required)
                      </label>
                      <textarea
                        value={waiveJustification}
                        onChange={(e) => setWaiveJustification(e.target.value)}
                        placeholder="Why is this violation acceptable?"
                        className="w-full px-2 py-1.5 text-[10px] border border-amber-200 rounded bg-white dark:bg-navy-800 resize-none"
                        rows={2}
                        autoFocus
                      />
                      {waiveError && (
                        <p className="text-[8px] text-red-600">{waiveError}</p>
                      )}
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => v.rule_id && submitWaive(v.rule_id)}
                          disabled={waiving || !waiveJustification.trim()}
                          className="flex-1 px-2 py-1 text-[8px] font-medium rounded bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed">
                          {waiving ? <Loader2 className="w-2.5 h-2.5 animate-spin inline" /> : "Submit Waiver"}
                        </button>
                        <button
                          onClick={() => { setWaivingId(null); setWaiveJustification(""); setWaiveError(null); }}
                          className="px-2 py-1 text-[8px] font-medium rounded border border-gray-200 text-gray-600 hover:bg-gray-50">
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * RecommendationsSection — Contextual AI recommendations with apply/dismiss.
 *
 * Shows:
 * - All recommendations with type badges (remediation, negotiation, fallback, best practice)
 * - Priority-based sorting
 * - Impact/effort matrix
 * - Apply/dismiss actions
 * - Linked findings
 */

"use client";

import React, { useState, useMemo, useCallback } from "react";
import {
  Lightbulb, Sparkles, CheckCircle2, XCircle, TrendingUp,
  BookOpen, Search, Target, Zap, ChevronDown, ChevronUp,
  ExternalLink, Loader2, FileText, CheckSquare, Square,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";
import { useApplyRecommendation, useDismissRecommendation } from "./hooks";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Recommendation } from "./types";

const TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  remediation: { icon: Lightbulb, color: "text-amber-600", bg: "bg-amber-100 dark:bg-amber-900/20", label: "Remediation" },
  negotiation: { icon: TrendingUp, color: "text-blue-600", bg: "bg-blue-100 dark:bg-blue-900/20", label: "Negotiation" },
  fallback: { icon: BookOpen, color: "text-purple-600", bg: "bg-purple-100 dark:bg-purple-900/20", label: "Fallback" },
  best_practice: { icon: Sparkles, color: "text-green-600", bg: "bg-green-100 dark:bg-green-900/20", label: "Best Practice" },
};

export function RecommendationsSection() {
  const ctx = useReviewContext();
  const { recommendations, findings, selectedReviewId } = ctx;
  const queryClient = useQueryClient();

  const generateRedlineMutation = useMutation({
    mutationFn: (rec: Recommendation) => {
      const finding = findings?.find(f => f.finding_id === rec.finding_id);
      const categoryMap: Record<string, string> = {
        liability: "liability_indemnity", indemnification: "liability_indemnity",
        data_protection: "data_protection", data_privacy: "data_protection",
        confidentiality: "confidentiality",
        ip: "intellectual_property", intellectual_property: "intellectual_property",
        term: "term_termination", termination: "term_termination",
        payment: "payment_audit", audit: "payment_audit",
        sla: "sla_support", support: "sla_support",
        assignment: "assignment_change_control",
        force_majeure: "force_majeure",
        governing_law: "governing_law_jurisdiction", jurisdiction: "governing_law_jurisdiction",
        insurance: "insurance",
        non_compete: "non_compete_exclusivity", exclusivity: "non_compete_exclusivity",
        other: "liability_indemnity",
      };
      const mitMap: Record<string, string> = {
        liability: "adding_liability_cap", indemnification: "narrowing_indemnity_scope",
        data_protection: "adding_dpa", data_privacy: "adding_dpa",
        confidentiality: "broadening_confidentiality",
        ip: "restricting_derivative_works", intellectual_property: "restricting_derivative_works",
        term: "extending_notice_period", termination: "adding_for_cause_termination",
        payment: "adding_price_protection", audit: "adding_audit_rights",
        sla: "adding_sla_guarantees", support: "adding_service_levels",
        assignment: "adding_change_of_control",
        force_majeure: "clarifying_warranty_scope",
        governing_law: "clarifying_governing_law", jurisdiction: "clarifying_governing_law",
        insurance: "adding_liability_cap",
        non_compete: "narrowing_ip_license", exclusivity: "narrowing_ip_license",
        other: "adding_liability_cap",
      };
      const ct = (finding?.clause_type || "").toLowerCase();
      return api.post(`/reviews/${selectedReviewId}/generate-mitigation-redline`, {
        mitigation_type: mitMap[ct] || "adding_liability_cap",
        clause_category: categoryMap[ct] || "liability_indemnity",
        finding_ids: rec.finding_id ? [rec.finding_id] : [],
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-redlines", selectedReviewId] });
    },
  });

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectMode, setSelectMode] = useState(false);

  const applyMutation = useApplyRecommendation();
  const dismissMutation = useDismissRecommendation();

  const recs = recommendations ?? [];

  const filtered = useMemo(() => {
    let r = [...recs];
    if (typeFilter) r = r.filter(rec => rec.type === typeFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      r = r.filter(rec => rec.title.toLowerCase().includes(q) || rec.clause_type.toLowerCase().includes(q));
    }
    r.sort((a, b) => a.priority - b.priority);
    return r;
  }, [recs, typeFilter, searchQuery]);

  const stats = useMemo(() => ({
    total: recs.length,
    pending: recs.filter(r => r.status === "pending").length,
    applied: recs.filter(r => r.status === "applied").length,
    highImpact: recs.filter(r => r.impact === "high" && r.status === "pending").length,
  }), [recs]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === filtered.filter(r => r.status === "pending").length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.filter(r => r.status === "pending").map(r => r.recommendation_id)));
    }
  }, [filtered, selectedIds]);

  const applySelected = useCallback(() => {
    if (!selectedReviewId) return;
    selectedIds.forEach(id => {
      applyMutation.mutate({ reviewId: selectedReviewId, recommendationId: id });
    });
    setSelectedIds(new Set());
    setSelectMode(false);
  }, [selectedReviewId, selectedIds, applyMutation]);

  const dismissSelected = useCallback(() => {
    if (!selectedReviewId) return;
    selectedIds.forEach(id => {
      dismissMutation.mutate({ reviewId: selectedReviewId, recommendationId: id });
    });
    setSelectedIds(new Set());
    setSelectMode(false);
  }, [selectedReviewId, selectedIds, dismissMutation]);

  return (
    <div className="p-4 space-y-3">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Total", value: stats.total, color: "text-gray-900 dark:text-white" },
          { label: "Pending", value: stats.pending, color: "text-blue-600" },
          { label: "Applied", value: stats.applied, color: "text-green-600" },
          { label: "High Impact", value: stats.highImpact, color: "text-red-600" },
        ].map(s => (
          <div key={s.label} className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-2.5 text-center">
            <div className={`text-base font-bold ${s.color}`}>{s.value}</div>
            <div className="text-[8px] text-gray-500 uppercase">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filter & Bulk Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[120px]">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search recommendations..." className="w-full pl-7 pr-2 py-1 text-[10px] bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400" />
        </div>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="text-[9px] px-2 py-1 rounded border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 text-navy-900 dark:text-white">
          <option value="">All Types</option>
          <option value="remediation">Remediation</option>
          <option value="negotiation">Negotiation</option>
          <option value="fallback">Fallback</option>
          <option value="best_practice">Best Practice</option>
        </select>
        <button onClick={() => { setSelectMode(!selectMode); if (selectMode) setSelectedIds(new Set()); }}
          className={`flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded border transition-colors ${
            selectMode ? "bg-navy-100 text-navy-700 border-navy-300 dark:bg-navy-700 dark:text-navy-200" : "bg-white text-gray-600 border-gray-200 dark:bg-navy-800 dark:text-gray-300"
          }`}>
          <CheckSquare className="w-2.5 h-2.5" /> Bulk
        </button>
      </div>

      {/* Bulk Action Bar */}
      {selectMode && selectedIds.size > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-navy-50 dark:bg-navy-750 border border-navy-200 dark:border-navy-600">
          <span className="text-[9px] text-gray-500 mr-1">{selectedIds.size} selected</span>
          <button onClick={toggleSelectAll} className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-white dark:bg-navy-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-navy-600 hover:bg-gray-50">
            {selectedIds.size === filtered.filter(r => r.status === "pending").length ? "Deselect All" : "Select All"}
          </button>
          <div className="w-px h-4 bg-gray-200 dark:bg-navy-600" />
          <button onClick={applySelected} disabled={applyMutation.isPending}
            className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50">
            {applyMutation.isPending ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <CheckCircle2 className="w-2.5 h-2.5" />}
            Apply Selected
          </button>
          <button onClick={dismissSelected} disabled={dismissMutation.isPending}
            className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-gray-500 text-white hover:bg-gray-600 disabled:opacity-50">
            {dismissMutation.isPending ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <XCircle className="w-2.5 h-2.5" />}
            Dismiss Selected
          </button>
        </div>
      )}

      {/* List */}
      <div className="space-y-1.5">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Sparkles className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
            <p className="text-xs text-gray-500">No recommendations available</p>
          </div>
        ) : filtered.map(rec => {
          const config = TYPE_CONFIG[rec.type] || TYPE_CONFIG.best_practice;
          const Icon = config.icon;
          const isExpanded = expandedId === rec.recommendation_id;

          return (
            <div key={rec.recommendation_id} className={`rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 overflow-hidden transition-shadow hover:shadow-sm ${rec.status === "applied" ? "opacity-60" : ""}`}>
              <div className="flex items-start">
                {selectMode && rec.status === "pending" && (
                  <button onClick={() => toggleSelect(rec.recommendation_id)} className="p-3 flex-shrink-0">
                    {selectedIds.has(rec.recommendation_id) ? (
                      <CheckSquare className="w-3.5 h-3.5 text-navy-600" />
                    ) : (
                      <Square className="w-3.5 h-3.5 text-gray-400" />
                    )}
                  </button>
                )}
                <button onClick={() => setExpandedId(isExpanded ? null : rec.recommendation_id)} className={`w-full flex items-start gap-2 px-3 py-2 text-left ${selectMode ? "pl-0" : ""}`}>
                <div className={`w-6 h-6 rounded-full ${config.bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-3 h-3 ${config.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`text-[8px] px-1 py-0.5 rounded-full ${config.bg} ${config.color} font-medium`}>{config.label}</span>
                    <span className="text-[10px] font-semibold text-navy-900 dark:text-white truncate">{rec.title}</span>
                    {rec.status === "applied" && <CheckCircle2 className="w-2.5 h-2.5 text-green-500" />}
                  </div>
                  <div className="flex items-center gap-2 text-[8px] text-gray-500">
                    <span>{rec.clause_type}</span>
                    <span className="flex items-center gap-0.5"><Zap className="w-2 h-2" />P{rec.priority}</span>
                    <span className="flex items-center gap-0.5"><Target className="w-2 h-2" />{Math.round(rec.confidence * 100)}%</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-[8px]">
                  <span className={`px-1 py-0.5 rounded font-medium ${
                    rec.impact === "high" ? "bg-red-100 text-red-700" :
                    rec.impact === "medium" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                  }`}>{rec.impact}</span>
                  <span className={`px-1 py-0.5 rounded font-medium ${
                    rec.effort === "low" ? "bg-green-100 text-green-700" :
                    rec.effort === "medium" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"
                  }`}>{rec.effort}</span>
                </div>
                {isExpanded ? <ChevronUp className="w-3 h-3 text-gray-400" /> : <ChevronDown className="w-3 h-3 text-gray-400" />}
              </button>
            </div>

            {isExpanded && (
                <div className="px-3 pb-2.5 space-y-2 border-t border-gray-100 dark:border-navy-700 pt-2">
                  <p className="text-[9px] text-gray-700 dark:text-gray-300">{rec.description}</p>

                  {/* Business Impact & Risk Reduction */}
                  <div className="grid grid-cols-2 gap-1.5">
                    <div className="p-1.5 rounded bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-800">
                      <span className="text-[7px] font-semibold text-red-700 uppercase">Business Impact</span>
                      <p className="text-[8px] text-gray-600 dark:text-gray-400 mt-0.5">
                        {rec.impact === "high" ? "Critical — requires immediate attention" :
                         rec.impact === "medium" ? "Moderate — address during review cycle" :
                         "Low — best practice improvement"}
                      </p>
                    </div>
                    <div className="p-1.5 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
                      <span className="text-[7px] font-semibold text-green-700 uppercase">Risk Reduction</span>
                      <div className="flex items-center gap-1 mt-0.5">
                        <div className="flex-1 h-1.5 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${
                            rec.impact === "high" ? "bg-green-500" :
                            rec.impact === "medium" ? "bg-amber-500" : "bg-blue-500"
                          }`} style={{ width: `${rec.impact === "high" ? 85 : rec.impact === "medium" ? 60 : 35}%` }} />
                        </div>
                        <span className="text-[8px] font-bold text-green-700">
                          {rec.impact === "high" ? "85%" : rec.impact === "medium" ? "60%" : "35%"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Fallback Language (Suggested Text) */}
                  {rec.suggested_text && (
                    <div className="p-1.5 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
                      <span className="text-[7px] font-semibold text-green-700 uppercase">Fallback Language</span>
                      <p className="text-[8px] text-gray-700 dark:text-gray-300 mt-0.5 font-mono leading-relaxed">&ldquo;{rec.suggested_text}&rdquo;</p>
                    </div>
                  )}

                  {/* Rationale */}
                  <div className="flex items-start gap-1 p-1.5 rounded bg-gray-50 dark:bg-navy-850">
                    <ExternalLink className="w-2 h-2 text-gray-400 mt-0.5 flex-shrink-0" />
                    <span className="text-[8px] text-gray-500">{rec.rationale}</span>
                  </div>

                  {/* Actions */}
                  {rec.status === "pending" && selectedReviewId && (
                    <div className="flex items-center gap-2 pt-0.5 flex-wrap">
                      {/* Locate Related Clause */}
                      <button onClick={() => {
                        import("@/lib/highlightClause").then(({ locateClause }) => {
                          locateClause({ page: 1, findingId: rec.finding_id || rec.recommendation_id, clauseText: rec.suggested_text || undefined });
                        });
                      }}
                        className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-cyan-100 text-cyan-700 hover:bg-cyan-200 border border-cyan-200 transition-colors">
                        <ExternalLink className="w-2.5 h-2.5" /> Locate Clause
                      </button>
                      <button onClick={() => applyMutation.mutate({ reviewId: selectedReviewId, recommendationId: rec.recommendation_id })}
                        className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 transition-colors">
                        <CheckCircle2 className="w-2.5 h-2.5" /> Apply
                      </button>
                      <button onClick={() => dismissMutation.mutate({ reviewId: selectedReviewId, recommendationId: rec.recommendation_id })}
                        className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200 transition-colors">
                        <XCircle className="w-2.5 h-2.5" /> Dismiss
                      </button>
                      {/* Linked Finding */}
                      {rec.finding_id && (() => {
                        const linkedFinding = findings?.find(f => f.finding_id === rec.finding_id);
                        return (
                          <div className="flex items-center gap-1.5 p-1.5 rounded bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-200 dark:border-indigo-800">
                            <ExternalLink className="w-2.5 h-2.5 text-indigo-500 flex-shrink-0" />
                            <span className="text-[8px] text-indigo-700 dark:text-indigo-300">
                              Finding: <strong>{linkedFinding?.title || rec.finding_id.slice(0, 8)}</strong>
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
                      {/* Generate Redline */}
                      <button onClick={() => generateRedlineMutation.mutate(rec)}
                        disabled={generateRedlineMutation.isPending}
                        className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 transition-colors disabled:opacity-50">
                        {generateRedlineMutation.isPending ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <FileText className="w-2.5 h-2.5" />}
                        {generateRedlineMutation.isPending ? "Generating..." : "Generate Redline"}
                      </button>
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

/**
 * FindingsSection — AI findings with inline explainability and AI feedback loop.
 *
 * Features:
 * - Severity-coded findings (red=critical, amber=high/medium, gray=low)
 * - Inline explainability: reasoning, confidence, similarity, benchmark deviation
 * - 4-dimension confidence breakdown (semantic, structural, linguistic, reference)
 * - AI feedback loop: mark correct/incorrect/partial
 * - Resolve/dismiss actions
 * - Jump between findings (N hotkey)
 * - Filter by severity and status
 */

"use client";

import React, { useState, useMemo, useCallback, useEffect } from "react";
import {
  Brain, AlertTriangle, CheckCircle2, XCircle, Lightbulb,
  ChevronDown, ChevronUp, Search, Filter, Target, TrendingUp,
  TrendingDown, Minus, BookOpen, FileText, ExternalLink,
  BarChart3, Cpu, ThumbsUp, ThumbsDown, HelpCircle, Loader2,
  SkipForward, Zap, GitCompare, Edit3, GitBranch,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";
import { useResolveFinding, useSubmitFeedback, useReviewRedlinesData } from "./hooks";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Finding, AiFeedback } from "./types";

export function FindingsSection() {
  const ctx = useReviewContext();
  const { findings, selectedFindingId, setSelectedFindingId, expandedFindingId, setExpandedFindingId, selectedReviewId, recommendations: ctxRecs } = ctx;

  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const resolveMutation = useResolveFinding();
  const feedbackMutation = useSubmitFeedback();
  const { data: redlines = [] } = useReviewRedlinesData(selectedReviewId ?? "");
  const queryClient = useQueryClient();

  // ── Map finding category → backend mitigation type ────────────────────
  const getMitigationParams = useCallback((finding: Finding) => {
    // Map clause_type to canonical category key
    const categoryMap: Record<string, string> = {
      liability: "liability_indemnity",
      indemnification: "liability_indemnity",
      data_protection: "data_protection",
      confidentiality: "confidentiality",
      ip: "intellectual_property",
      intellectual_property: "intellectual_property",
      term: "term_termination",
      termination: "term_termination",
      payment: "payment_audit",
      audit: "payment_audit",
      sla: "sla_support",
      support: "sla_support",
      assignment: "assignment_change_control",
      force_majeure: "force_majeure",
      governing_law: "governing_law_jurisdiction",
      jurisdiction: "governing_law_jurisdiction",
      insurance: "insurance",
      non_compete: "non_compete_exclusivity",
      exclusivity: "non_compete_exclusivity",
    };
    // Map clause_type to a default mitigation type
    const mitMap: Record<string, string> = {
      liability: "adding_liability_cap",
      indemnification: "narrowing_indemnity_scope",
      data_protection: "adding_dpa",
      confidentiality: "broadening_confidentiality",
      ip: "restricting_derivative_works",
      intellectual_property: "restricting_derivative_works",
      term: "extending_notice_period",
      sla: "adding_sla_guarantees",
      assignment: "adding_change_of_control",
    };
    const clauseType = (finding.clause_type || "").toLowerCase();
    return {
      mitigation_type: mitMap[clauseType] || "adding_liability_cap",
      clause_category: categoryMap[clauseType] || "liability_indemnity",
    };
  }, []);

  const generateRedlineMutation = useMutation({
    mutationFn: (finding: Finding) => {
      const { mitigation_type, clause_category } = getMitigationParams(finding);
      return api.post(`/reviews/${selectedReviewId}/generate-mitigation-redline`, {
        mitigation_type,
        clause_category,
        finding_ids: [finding.finding_id],
      });
    },
    onSuccess: (data, finding) => {
      queryClient.invalidateQueries({ queryKey: ["review-redlines", selectedReviewId] });
      // ── Risk Reduction ↔ Redline Integration ──
      // Step 1: Resolve the finding (marks it as resolved in backend)
      resolveMutation.mutate({ reviewId: selectedReviewId!, findingId: finding.finding_id, resolution: "resolved" });
      // Step 2: Invalidate findings to reflect resolved status
      queryClient.invalidateQueries({ queryKey: ["review-findings", selectedReviewId] });
      // Step 3: Invalidate risk data so RiskReductionSection picks up the change
      queryClient.invalidateQueries({ queryKey: ["review-risk", selectedReviewId] });
      // Step 4: Invalidate audit trail for the new audit record
      queryClient.invalidateQueries({ queryKey: ["review-audit", selectedReviewId] });
    },
  });

  // ── Build finding → redline lookup ───────────────────────────────────

  const redlineByFinding = useMemo(() => {
    const map = new Map<string, typeof redlines[0]>();
    redlines.forEach(r => {
      if (r.finding_id) map.set(r.finding_id, r);
    });
    return map;
  }, [redlines]);

  // ── Next / Previous navigation ───────────────────────────────────────

  const openFindings = useMemo(
    () => findings.filter(f => (f.status || "open") === "open"),
    [findings],
  );

  const currentIdx = useMemo(() => {
    if (!selectedFindingId) return -1;
    return openFindings.findIndex(f => f.finding_id === selectedFindingId);
  }, [selectedFindingId, openFindings]);

  const navigateToFinding = useCallback((direction: "prev" | "next" | "next_unreviewed") => {
    if (openFindings.length === 0) return;
    let nextIdx = -1;
    if (direction === "next") {
      nextIdx = currentIdx < 0 ? 0 : (currentIdx + 1) % openFindings.length;
    } else if (direction === "prev") {
      nextIdx = currentIdx <= 0 ? openFindings.length - 1 : currentIdx - 1;
    } else if (direction === "next_unreviewed") {
      // Find the next finding that hasn't been resolved/dismissed
      nextIdx = openFindings.findIndex((f, i) => i > currentIdx && (f.status || "open") === "open");
      if (nextIdx < 0) {
        // Wrap around
        nextIdx = openFindings.findIndex(f => (f.status || "open") === "open");
      }
    }
    if (nextIdx >= 0) {
      setSelectedFindingId(openFindings[nextIdx].finding_id);
      setExpandedFindingId(openFindings[nextIdx].finding_id);
    }
  }, [openFindings, currentIdx, setSelectedFindingId, setExpandedFindingId]);

  // Auto-expand first open finding on initial load
  useEffect(() => {
    if (findings.length > 0 && !expandedFindingId && !selectedFindingId) {
      const firstOpen = findings.find(f => (f.status || "open") === "open");
      if (firstOpen) {
        setSelectedFindingId(firstOpen.finding_id);
        setExpandedFindingId(firstOpen.finding_id);
      }
    }
  }, [findings.length]);

  // Listen for keyboard resolve events from the platform
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.findingId && selectedReviewId) {
        resolveMutation.mutate({ reviewId: selectedReviewId, findingId: detail.findingId, resolution: "resolved" });
      }
    };
    window.addEventListener("finding:resolve", handler);
    return () => window.removeEventListener("finding:resolve", handler);
  }, [selectedReviewId, resolveMutation]);

  // Filter
  const filtered = useMemo(() => {
    let r = [...findings];
    if (severityFilter) r = r.filter(f => f.severity === severityFilter);
    if (statusFilter) r = r.filter(f => (f.status || "open") === statusFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      r = r.filter(f => f.title.toLowerCase().includes(q) || f.clause_type.toLowerCase().includes(q) || f.description.toLowerCase().includes(q));
    }
    return r;
  }, [findings, severityFilter, statusFilter, searchQuery]);

  const handleResolve = useCallback((findingId: string) => {
    if (!selectedReviewId) return;
    resolveMutation.mutate({ reviewId: selectedReviewId, findingId, resolution: "resolved" });
  }, [selectedReviewId, resolveMutation]);

  const handleFeedback = useCallback((findingId: string, type: AiFeedback["type"]) => {
    if (!selectedReviewId) return;
    feedbackMutation.mutate({ reviewId: selectedReviewId, findingId, feedback: { type, reviewer_note: "", retraining_priority: "medium", retraining_status: "pending" } as any });
  }, [selectedReviewId, feedbackMutation]);

  const stats = useMemo(() => ({
    total: findings.length,
    critical: findings.filter(f => f.severity === "critical" && (f.status || "open") === "open").length,
    open: findings.filter(f => (f.status || "open") === "open").length,
    resolved: findings.filter(f => (f.status || "open") === "resolved" || (f.status || "open") === "dismissed").length,
  }), [findings]);

  return (
    <div className="flex flex-col h-full">
      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-px bg-gray-100 dark:bg-navy-700">
        {[
          { label: "Total", value: stats.total, color: "text-gray-900 dark:text-white" },
          { label: "Open", value: stats.open, color: "text-amber-600" },
          { label: "Critical", value: stats.critical, color: "text-red-600" },
          { label: "Resolved", value: stats.resolved, color: "text-green-600" },
        ].map(s => (
          <div key={s.label} className="bg-white dark:bg-navy-800 px-3 py-2 text-center">
            <div className={`text-sm font-bold ${s.color}`}>{s.value}</div>
            <div className="text-[9px] text-gray-500 uppercase">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Navigation bar */}
      <div className="flex items-center gap-1 px-3 py-1.5 border-b border-gray-100 dark:border-navy-700 bg-gray-50/50 dark:bg-navy-800/50">
        <button
          onClick={() => navigateToFinding("prev")}
          disabled={openFindings.length === 0}
          className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded text-gray-600 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-navy-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          title="Previous finding"
        >
          <ChevronDown className="w-3 h-3 rotate-90" /> Prev
        </button>
        <span className="text-[9px] text-gray-400">
          {currentIdx >= 0 ? `${currentIdx + 1}` : "—"}/{openFindings.length} open
        </span>
        <button
          onClick={() => navigateToFinding("next")}
          disabled={openFindings.length === 0}
          className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded text-gray-600 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-navy-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          title="Next finding"
        >
          Next <ChevronDown className="w-3 h-3 -rotate-90" />
        </button>
        <div className="w-px h-4 bg-gray-200 dark:bg-navy-600 mx-1" />
        <button
          onClick={() => navigateToFinding("next_unreviewed")}
          disabled={openFindings.length === 0}
          className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-300 dark:hover:bg-blue-900/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          title="Jump to next unreviewed finding"
        >
          <SkipForward className="w-3 h-3" /> Next Unreviewed
        </button>
      </div>

      {/* Search & Filter */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 dark:border-navy-700">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search findings... (N for next)" className="w-full pl-7 pr-2 py-1 text-[11px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400" />
        </div>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="text-[10px] px-2 py-1 rounded border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white">
          <option value="">All Severity</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="text-[10px] px-2 py-1 rounded border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white">
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>

      {/* Findings List */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <Brain className="w-10 h-10 text-gray-300 dark:text-gray-600 mb-2" />
            <p className="text-xs text-gray-500">No findings match your filters</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-navy-700">
            {filtered.map(finding => {
              const isSelected = selectedFindingId === finding.finding_id;
              const isExpanded = expandedFindingId === finding.finding_id;

              return (
                <div key={finding.finding_id} className={`transition-colors ${isSelected ? "bg-navy-50 dark:bg-navy-750 ring-1 ring-navy-300 dark:ring-navy-500" : ""}`}>
                  {/* Header Row */}
                  <button
                    onClick={() => { setSelectedFindingId(finding.finding_id); setExpandedFindingId(isExpanded ? null : finding.finding_id); }}
                    className="w-full flex items-start gap-2 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-navy-750"
                  >
                    <span className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${
                      finding.severity === "critical" ? "bg-red-500" :
                      finding.severity === "high" ? "bg-red-400" :
                      finding.severity === "medium" ? "bg-amber-500" : "bg-gray-400"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className={`text-[11px] font-semibold ${
                          finding.severity === "critical" ? "text-red-700" :
                          finding.severity === "high" ? "text-red-600" :
                          finding.severity === "medium" ? "text-amber-700" : "text-gray-700"
                        }`}>{finding.title}</span>
                        {/* Review status badge */}
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium ${
                          (finding.status || "open") === "open" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" :
                          (finding.status || "open") === "resolved" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" :
                          (finding.status || "open") === "dismissed" ? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400" :
                          (finding.status || "open") === "accepted" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" :
                          (finding.status || "open") === "rejected" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300" :
                          (finding.status || "open") === "modified" ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300" :
                          (finding.status || "open") === "waived" ? "bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300" :
                          (finding.status || "open") === "escalated" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300" :
                          (finding.status || "open") === "mitigated" ? "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300" :
                          "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                        }`}>
                          {(finding.status || "open") === "open" && "Pending"}
                          {(finding.status || "open") === "resolved" && "Resolved"}
                          {(finding.status || "open") === "dismissed" && "Dismissed"}
                          {(finding.status || "open") === "accepted" && "Accepted"}
                          {(finding.status || "open") === "rejected" && "Rejected"}
                          {(finding.status || "open") === "modified" && "Modified"}
                          {(finding.status || "open") === "waived" && "Waived"}
                          {(finding.status || "open") === "escalated" && "Escalated"}
                          {(finding.status || "open") === "mitigated" && "Mitigated"}
                          {!["open", "resolved", "dismissed", "accepted", "rejected", "modified", "waived", "escalated", "mitigated"].includes(finding.status || "open") && (finding.status || "open").replace(/_/g, " ")}
                        </span>
                        {/* Finding → Redline badge */}
                        {redlineByFinding.has(finding.finding_id) && (
                          <span className="text-[8px] px-1.5 py-0.5 rounded-full font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 flex items-center gap-0.5">
                            <Edit3 className="w-2 h-2" /> Redline Generated
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[9px] text-gray-500">
                        <span className="px-1 py-0.5 rounded bg-gray-100 dark:bg-navy-700">{finding.clause_type}</span>
                        <span className="flex items-center gap-0.5"><Target className="w-2.5 h-2.5" />{Math.round(finding.confidence * 100)}%</span>
                        {finding.page_numbers.length > 0 && <span>p.{finding.page_numbers.join(",")}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-[9px]">
                      {finding.benchmark_deviation != null && finding.benchmark_deviation > 0.3 && (
                        <span className="px-1 py-0.5 rounded bg-red-100 text-red-700 font-medium">
                          {(finding.benchmark_deviation * 100).toFixed(0)}% dev
                        </span>
                      )}
                      {isExpanded ? <ChevronUp className="w-3 h-3 text-gray-400" /> : <ChevronDown className="w-3 h-3 text-gray-400" />}
                    </div>
                  </button>

                  {/* Expanded: Description + Explainability + Actions */}
                  {isExpanded && (() => {
                    const linkedRedline = redlineByFinding.get(finding.finding_id);
                    return (
                    <div className="px-3 pb-3 space-y-2.5 border-t border-gray-50 dark:border-navy-750 pt-2">
                      {/* Description */}
                      <p className="text-[10px] text-gray-700 dark:text-gray-300 leading-relaxed">{finding.description}</p>

                      {/* ── Source Mapping ──────────────────────────────── */}
                      <div className="grid grid-cols-2 gap-1.5">
                        {finding.clause_text && (
                          <div className="rounded-lg bg-gray-50 dark:bg-navy-750 p-2 border border-gray-100 dark:border-navy-700 col-span-2">
                            <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5">Source Clause</p>
                            <p className="text-[8px] text-gray-700 dark:text-gray-300 leading-relaxed line-clamp-3 font-mono">
                              {finding.clause_text}
                            </p>
                          </div>
                        )}
                        <div className="rounded-lg bg-gray-50 dark:bg-navy-750 p-2 border border-gray-100 dark:border-navy-700">
                          <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5">Location</p>
                          <div className="space-y-0.5 text-[8px] text-gray-600 dark:text-gray-400">
                            {finding.page_numbers.length > 0 && <p>Page: <span className="font-medium text-navy-900 dark:text-white">{finding.page_numbers.join(", ")}</span></p>}
                            {finding.clause_type && <p>Section: <span className="font-medium text-navy-900 dark:text-white">{finding.clause_type.replace(/_/g, " ")}</span></p>}
                            <p>Finding ID: <span className="font-mono text-[7px] text-gray-400">{finding.finding_id.slice(0, 8)}…</span></p>
                          </div>
                        </div>
                        <div className="rounded-lg bg-gray-50 dark:bg-navy-750 p-2 border border-gray-100 dark:border-navy-700">
                          <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5">Matched Policy</p>
                          {finding.matched_corpus ? (
                            <div className="space-y-0.5 text-[8px]">
                              <p className="text-gray-600 dark:text-gray-400 truncate" title={finding.matched_corpus}>
                                <BookOpen className="w-2 h-2 inline mr-0.5" />{finding.matched_corpus}
                              </p>
                              {finding.benchmark_deviation != null && (
                                <p className="text-gray-500">
                                  Deviation: <span className={`font-medium ${Math.abs(finding.benchmark_deviation) > 0.3 ? "text-red-600" : "text-amber-600"}`}>
                                    {(finding.benchmark_deviation * 100).toFixed(1)}%
                                  </span>
                                </p>
                              )}
                            </div>
                          ) : (
                            <p className="text-[8px] text-gray-400 italic">No policy match</p>
                          )}
                        </div>
                      </div>

                      {/* Business Impact */}
                      {finding.business_impact && (
                        <div className="flex items-start gap-1.5 p-2 rounded bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-800">
                          <AlertTriangle className="w-3 h-3 text-red-500 mt-0.5 flex-shrink-0" />
                          <span className="text-[9px] text-red-700 dark:text-red-300">{finding.business_impact}</span>
                        </div>
                      )}

                      {/* Recommended Mitigation */}
                      {finding.recommended_mitigation && (
                        <div className="flex items-start gap-1.5 p-2 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-800">
                          <Lightbulb className="w-3 h-3 text-blue-500 mt-0.5 flex-shrink-0" />
                          <span className="text-[9px] text-blue-700 dark:text-blue-300">{finding.recommended_mitigation}</span>
                        </div>
                      )}

                      {/* ── Finding → Redline Traceability ────────────────── */}
                      {(() => {
                        const lr = redlineByFinding.get(finding.finding_id);
                        if (!lr) return null;
                        return (
                          <div className="flex items-center gap-2 p-2 rounded-lg bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800">
                            <Edit3 className="w-3 h-3 text-purple-500 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-[8px] font-semibold text-purple-700 dark:text-purple-300">Finding → Redline Generated</p>
                              <p className="text-[8px] text-purple-600 dark:text-purple-400 truncate">
                                {lr.clause_type} §{lr.section} · {lr.status}
                              </p>
                            </div>
                            <span className={`text-[7px] font-medium px-1.5 py-0.5 rounded-full ${
                              lr.status === "accepted" ? "bg-green-100 text-green-700" :
                              lr.status === "rejected" ? "bg-gray-100 text-gray-500" :
                              lr.status === "modified" ? "bg-purple-100 text-purple-700" :
                              "bg-amber-100 text-amber-700"
                            }`}>{lr.status}</span>
                          </div>
                        );
                      })()}

                      {/* ── AI Explainability — Redesigned: Source → Reason → Policy → Benchmark → Fix ── */}
                      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-850 overflow-hidden">
                        <div className="px-2.5 py-1.5 bg-gray-100 dark:bg-navy-800 flex items-center gap-1.5">
                          <Brain className="w-3 h-3 text-purple-500" />
                          <span className="text-[9px] font-semibold text-gray-600 dark:text-gray-400 uppercase">AI Explainability</span>
                          {/* Confidence — compact secondary badge */}
                          {finding.confidence != null && (
                            <span className={`ml-auto text-[7px] font-medium px-1.5 py-0.5 rounded-full ${
                              finding.confidence >= 0.8 ? 'bg-green-100 text-green-700' :
                              finding.confidence >= 0.6 ? 'bg-amber-100 text-amber-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {(finding.confidence * 100).toFixed(0)}% confidence
                            </span>
                          )}
                        </div>
                        <div className="p-2.5 space-y-2">
                          {/* 1. Source Text */}
                          {finding.clause_text && (
                            <div className="rounded bg-white dark:bg-navy-800 p-2 border border-gray-150 dark:border-navy-700">
                              <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5 flex items-center gap-1">
                                <FileText className="w-2.5 h-2.5" /> Source Text
                              </p>
                              <p className="text-[9px] text-gray-700 dark:text-gray-300 leading-relaxed font-mono">{finding.clause_text}</p>
                            </div>
                          )}

                          {/* 2. Reason */}
                          {finding.reasoning && (
                            <div>
                              <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5 flex items-center gap-1">
                                <Lightbulb className="w-2.5 h-2.5" /> Reason
                              </p>
                              <p className="text-[9px] text-gray-700 dark:text-gray-300 leading-relaxed">{finding.reasoning}</p>
                            </div>
                          )}

                          {/* 3. Policy Trigger */}
                          <div className="grid grid-cols-2 gap-2">
                            <div className="rounded bg-white dark:bg-navy-800 p-2 border border-gray-150 dark:border-navy-700">
                              <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5 flex items-center gap-1">
                                <BookOpen className="w-2.5 h-2.5" /> Policy Trigger
                              </p>
                              {finding.matched_corpus ? (
                                <div>
                                  <p className="text-[9px] font-medium text-navy-900 dark:text-white truncate" title={finding.matched_corpus}>{finding.matched_corpus}</p>
                                  {finding.benchmark_deviation != null && (
                                    <p className="text-[8px] text-gray-500 mt-0.5">
                                      Deviation: <span className={`font-medium ${Math.abs(finding.benchmark_deviation) > 0.3 ? "text-red-600" : "text-amber-600"}`}>
                                        {(finding.benchmark_deviation * 100).toFixed(1)}%
                                      </span>
                                    </p>
                                  )}
                                </div>
                              ) : (
                                <p className="text-[9px] text-gray-400 italic">No policy match</p>
                              )}
                            </div>
                            <div className="rounded bg-white dark:bg-navy-800 p-2 border border-gray-150 dark:border-navy-700">
                              <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5 flex items-center gap-1">
                                <BarChart3 className="w-2.5 h-2.5" /> Industry Benchmark
                              </p>
                              {finding.similarity_score != null ? (
                                <div>
                                  <p className="text-[9px] font-medium text-navy-900 dark:text-white">
                                    Similarity: <span className={`${finding.similarity_score >= 0.8 ? "text-green-600" : finding.similarity_score >= 0.6 ? "text-amber-600" : "text-red-600"}`}>
                                      {(finding.similarity_score * 100).toFixed(0)}%
                                    </span>
                                  </p>
                                  {finding.benchmark_deviation != null && (
                                    <p className="text-[8px] text-gray-500 mt-0.5 flex items-center gap-0.5">
                                      {finding.benchmark_deviation > 0 ? <TrendingUp className="w-2 h-2 text-red-500" /> : <TrendingDown className="w-2 h-2 text-green-500" />}
                                      {(finding.benchmark_deviation * 100).toFixed(1)}% from market
                                    </p>
                                  )}
                                </div>
                              ) : (
                                <p className="text-[9px] text-gray-400 italic">No benchmark data</p>
                              )}
                            </div>
                          </div>

                          {/* 4. Recommended Fix */}
                          {finding.recommended_mitigation && (
                            <div className="rounded bg-blue-50 dark:bg-blue-900/10 p-2 border border-blue-100 dark:border-blue-800">
                              <p className="text-[7px] font-semibold text-blue-600 dark:text-blue-400 uppercase mb-0.5 flex items-center gap-1">
                                <Target className="w-2.5 h-2.5" /> Recommended Fix
                              </p>
                              <p className="text-[9px] text-blue-700 dark:text-blue-300 leading-relaxed">{finding.recommended_mitigation}</p>
                            </div>
                          )}

                          {/* 5. Supporting Evidence — collapsed under expand */}
                          {finding.supporting_evidence?.length > 0 && (
                            <details className="group">
                              <summary className="text-[7px] font-semibold text-gray-400 uppercase cursor-pointer hover:text-gray-600 flex items-center gap-1">
                                <ChevronDown className="w-2.5 h-2.5 group-open:rotate-180 transition-transform" />
                                Supporting Evidence ({finding.supporting_evidence.length})
                              </summary>
                              <ul className="mt-1 space-y-0.5 pl-3">
                                {finding.supporting_evidence.map((ev, i) => (
                                  <li key={i} className="flex items-start gap-1 text-[8px] text-gray-500">
                                    <FileText className="w-2 h-2 mt-0.5 flex-shrink-0" />
                                    {ev}
                                  </li>
                                ))}
                              </ul>
                            </details>
                          )}

                          {/* Confidence breakdown — subtle, secondary */}
                          <details className="group">
                            <summary className="text-[7px] font-semibold text-gray-400 uppercase cursor-pointer hover:text-gray-600 flex items-center gap-1">
                              <ChevronDown className="w-2.5 h-2.5 group-open:rotate-180 transition-transform" />
                              Confidence Breakdown
                            </summary>
                            <div className="mt-1 space-y-0.5 pl-1">
                              {[
                                { label: "Semantic", value: finding.confidence_semantic },
                                { label: "Structural", value: finding.confidence_structural },
                                { label: "Linguistic", value: finding.confidence_linguistic },
                                { label: "Reference", value: finding.confidence_reference },
                              ].map(c => c.value != null ? (
                                <div key={c.label} className="flex items-center gap-1.5">
                                  <span className="text-[7px] text-gray-400 w-12 text-right">{c.label}</span>
                                  <div className="flex-1 h-1 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full ${c.value >= 0.8 ? "bg-green-400" : c.value >= 0.6 ? "bg-amber-400" : "bg-red-400"}`}
                                      style={{ width: `${c.value * 100}%` }} />
                                  </div>
                                  <span className="text-[7px] font-medium text-gray-500 w-5">{(c.value * 100).toFixed(0)}%</span>
                                </div>
                              ) : null)}
                            </div>
                          </details>
                        </div>
                      </div>

                      {/* ── Traceability Chain ─────────────────────────────── */}
                      {(() => {
                        const linkedRedline = redlineByFinding.get(finding.finding_id);
                        const linkedRec = ctx.recommendations?.find(r => r.finding_id === finding.finding_id);
                        return (
                          <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-850 overflow-hidden">
                            <div className="px-2.5 py-1.5 bg-gray-100 dark:bg-navy-800 flex items-center gap-1.5">
                              <GitCompare className="w-3 h-3 text-emerald-500" />
                              <span className="text-[9px] font-semibold text-gray-600 dark:text-gray-400 uppercase">Traceability Chain</span>
                            </div>
                            <div className="p-2.5">
                              <div className="flex items-center gap-1.5 text-[8px]">
                                {/* Clause */}
                                <button onClick={() => {
                                  import("@/lib/highlightClause").then(({ locateClause }) => {
                                    locateClause({
                                      page: finding.page_numbers[0] || 1,
                                      findingId: finding.finding_id,
                                      clauseText: finding.clause_text || undefined,
                                    });
                                  });
                                }}
                                  className="flex items-center gap-1 px-2 py-1 rounded bg-cyan-100 text-cyan-700 font-medium hover:bg-cyan-200 transition-colors cursor-pointer">
                                  <ExternalLink className="w-2.5 h-2.5" /> Clause
                                </button>
                                <ChevronDown className="w-2.5 h-2.5 text-gray-300 -rotate-90" />
                                {/* Finding */}
                                <div className="flex items-center gap-1 px-2 py-1 rounded bg-blue-100 text-blue-700 font-medium">
                                  <Brain className="w-2.5 h-2.5" /> Finding
                                </div>
                                <ChevronDown className="w-2.5 h-2.5 text-gray-300 -rotate-90" />
                                {/* Recommendation */}
                                <div className={`flex items-center gap-1 px-2 py-1 rounded font-medium ${linkedRec ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-400"}`}>
                                  <Lightbulb className="w-2.5 h-2.5" /> Rec
                                </div>
                                <ChevronDown className="w-2.5 h-2.5 text-gray-300 -rotate-90" />
                                {/* Redline */}
                                <div className={`flex items-center gap-1 px-2 py-1 rounded font-medium ${linkedRedline ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-400"}`}>
                                  <Edit3 className="w-2.5 h-2.5" /> Redline
                                </div>
                                <ChevronDown className="w-2.5 h-2.5 text-gray-300 -rotate-90" />
                                {/* Version */}
                                <div className={`flex items-center gap-1 px-2 py-1 rounded font-medium ${false ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}>
                                  <GitCompare className="w-2.5 h-2.5" /> Version
                                </div>
                                <ChevronDown className="w-2.5 h-2.5 text-gray-300 -rotate-90" />
                                {/* Approval */}
                                <div className={`flex items-center gap-1 px-2 py-1 rounded font-medium ${false ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}>
                                  <CheckCircle2 className="w-2.5 h-2.5" /> Approval
                                </div>
                              </div>
                              {(linkedRec || linkedRedline) && (
                                <div className="mt-1.5 space-y-0.5 text-[8px] text-gray-500">
                                  {linkedRec && <p>→ Recommendation: {linkedRec.title} ({linkedRec.status})</p>}
                                  {linkedRedline && <p>→ Redline: {linkedRedline.clause_type} §{linkedRedline.section} · {linkedRedline.status}</p>}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })()}

                      {/* ── Deep Drill Down: Clause Location, Similar Contracts, Benchmark ── */}
                      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-850 overflow-hidden">
                        <div className="px-2.5 py-1.5 bg-gray-100 dark:bg-navy-800 flex items-center gap-1.5">
                          <Search className="w-3 h-3 text-cyan-500" />
                          <span className="text-[9px] font-semibold text-gray-600 dark:text-gray-400 uppercase">Deep Drill Down</span>
                        </div>
                        <div className="p-2.5 space-y-2">
                          {/* Locate Clause */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <FileText className="w-2.5 h-2.5 text-gray-400" />
                              <span className="text-[8px] text-gray-500">Clause Location</span>
                            </div>
                            <div className="flex items-center gap-1">
                              {finding.page_numbers.length > 0 && (
                                <span className="text-[8px] font-medium text-navy-900 dark:text-white">
                                  p.{finding.page_numbers.join(", ")}
                                </span>
                              )}
                              <button className="flex items-center gap-0.5 px-1.5 py-0.5 text-[7px] font-medium rounded bg-cyan-100 text-cyan-700 hover:bg-cyan-200 transition-colors">
                                <ExternalLink className="w-2 h-2" /> Jump to Page
                              </button>
                            </div>
                          </div>

                          {/* Clause Text Preview */}
                          {finding.clause_text && (
                            <div className="p-1.5 rounded bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
                              <p className="text-[7px] font-semibold text-gray-500 uppercase mb-0.5">Clause Text</p>
                              <p className="text-[8px] text-gray-600 dark:text-gray-400 leading-relaxed line-clamp-2">{finding.clause_text}</p>
                            </div>
                          )}

                          {/* Similar Contracts */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <BookOpen className="w-2.5 h-2.5 text-gray-400" />
                              <span className="text-[8px] text-gray-500">Similar Contracts</span>
                            </div>
                            <span className="text-[8px] font-medium text-gray-600 dark:text-gray-400">
                              {finding.similarity_score != null
                                ? `${(finding.similarity_score * 100).toFixed(0)}% match`
                                : "—"}
                            </span>
                          </div>

                          {/* Benchmark Clause Comparison */}
                          {finding.benchmark_deviation != null && (
                            <div className="p-1.5 rounded bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
                              <p className="text-[7px] font-semibold text-gray-500 uppercase mb-1">Benchmark Comparison</p>
                              <div className="grid grid-cols-3 gap-1 text-[7px]">
                                <div className="p-1 rounded bg-green-50 text-green-700 text-center font-medium">Standard</div>
                                <div className="p-1 rounded bg-amber-50 text-amber-700 text-center font-medium">Current</div>
                                <div className="p-1 rounded bg-red-50 text-red-700 text-center font-medium">Difference</div>
                              </div>
                              <div className="mt-1 flex items-center justify-between text-[8px]">
                                <span className="text-gray-400">Deviation from market</span>
                                <span className={`font-bold ${
                                  Math.abs(finding.benchmark_deviation) > 0.3 ? "text-red-600" : "text-amber-600"
                                }`}>
                                  {finding.benchmark_deviation > 0 ? "+" : ""}{(finding.benchmark_deviation * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>
                          )}

                          {/* Corpus Match */}
                          {finding.matched_corpus && (
                            <div className="text-[7px] text-gray-400 truncate">
                              <BookOpen className="w-2 h-2 inline mr-0.5" />
                              Corpus: {finding.matched_corpus}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* ── Reviewer Assessment (shown when feedback exists) ── */}
                      {finding.feedback_type && (
                        <div className="pt-1">
                          <div className="rounded border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/10 px-2 py-1.5">
                            <div className="flex items-center gap-1.5 mb-0.5">
                              {finding.feedback_type === "correct" && <ThumbsUp className="w-3 h-3 text-green-600" />}
                              {finding.feedback_type === "incorrect" && <ThumbsDown className="w-3 h-3 text-red-600" />}
                              {finding.feedback_type === "partial" && <HelpCircle className="w-3 h-3 text-amber-600" />}
                              <span className="text-[9px] font-semibold text-gray-700 dark:text-gray-200">Reviewer Assessment</span>
                            </div>
                            <div className="text-[8px] text-gray-500 dark:text-gray-400">
                              <span className="font-medium capitalize text-gray-600 dark:text-gray-300">{finding.feedback_type}</span>
                              <span className="mx-1">·</span>
                              <span>Reviewed by: {finding.resolved_by || "Current user"}</span>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* ── AI Feedback Loop ──────────────────────────────── */}
                      {(finding.status || "open") === "open" && (
                        <div className="flex items-center gap-2 pt-1">
                          <span className="text-[8px] font-semibold text-gray-500 uppercase">AI Feedback:</span>
                          {[
                            { type: "correct" as const, icon: ThumbsUp, label: "Correct", color: "text-green-600 bg-green-50 border-green-200 hover:bg-green-100", activeColor: "bg-green-600 text-white border-green-600" },
                            { type: "incorrect" as const, icon: ThumbsDown, label: "Incorrect", color: "text-red-600 bg-red-50 border-red-200 hover:bg-red-100", activeColor: "bg-red-600 text-white border-red-600" },
                            { type: "partial" as const, icon: HelpCircle, label: "Partial", color: "text-amber-600 bg-amber-50 border-amber-200 hover:bg-amber-100", activeColor: "bg-amber-600 text-white border-amber-600" },
                          ].map(btn => {
                            const isActive = finding.feedback_type === btn.type;
                            return (
                              <button key={btn.type} onClick={() => handleFeedback(finding.finding_id, btn.type)}
                                className={`flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-medium rounded border transition-colors ${
                                  isActive ? btn.activeColor : btn.color
                                }`}>
                                <btn.icon className="w-2.5 h-2.5" /> {btn.label}
                              </button>
                            );
                          })}
                        </div>
                      )}

                      {/* ── Finding → Redline → Policy Linkage ── */}
                      {linkedRedline && (
                        <div className="mt-2 p-2 rounded-md bg-indigo-50/70 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800/40">
                          <div className="flex items-center gap-1.5 mb-1">
                            <GitBranch className="w-3 h-3 text-indigo-500" />
                            <span className="text-[8px] font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Linked Redline</span>
                            <span className={`ml-auto text-[7px] font-medium px-1.5 py-0.5 rounded-full ${
                              linkedRedline.status === 'accepted' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                              linkedRedline.status === 'pending' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                              'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                            }`}>
                              {linkedRedline.status || 'Pending'}
                            </span>
                          </div>
                          <div className="grid grid-cols-3 gap-1.5 text-[8px]">
                            <div className="flex flex-col">
                              <span className="text-gray-400 dark:text-gray-500">Policy Fixed</span>
                              <span className="font-medium text-gray-700 dark:text-gray-300">
                                {linkedRedline.impact?.policyFixed ?? '—'}
                              </span>
                            </div>
                            <div className="flex flex-col">
                              <span className="text-gray-400 dark:text-gray-500">Risk Reduction</span>
                              <span className={`font-medium ${
                                (linkedRedline.impact?.riskReduction ?? 0) >= 70 ? 'text-green-600' :
                                (linkedRedline.impact?.riskReduction ?? 0) >= 40 ? 'text-amber-600' :
                                'text-gray-600'
                              }`}>
                                {linkedRedline.impact?.riskReduction != null ? `${linkedRedline.impact.riskReduction}%` : '—'}
                              </span>
                            </div>
                            <div className="flex flex-col">
                              <span className="text-gray-400 dark:text-gray-500">Findings Resolved</span>
                              <span className="font-medium text-gray-700 dark:text-gray-300">
                                {linkedRedline.impact?.findingsResolved ?? '—'}
                              </span>
                            </div>
                          </div>
                          {linkedRedline.redline_text && (
                            <div className="mt-1.5 pt-1.5 border-t border-indigo-200/50 dark:border-indigo-800/30">
                              <span className="text-[7px] text-gray-400 dark:text-gray-500">Redline Preview</span>
                              <p className="text-[8px] text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-2 leading-relaxed">
                                {linkedRedline.redline_text}
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* ── Primary Actions: Locate, Generate Redline, Dismiss, Resolve ── */}
                      {(finding.status || "open") === "open" && (
                        <div className="flex items-center gap-2 pt-1 flex-wrap">
                          {/* Locate Clause — navigates document viewer */}
                          <button onClick={() => {
                            import("@/lib/highlightClause").then(({ locateClause }) => {
                              locateClause({
                                page: finding.page_numbers[0] || 1,
                                findingId: finding.finding_id,
                                clauseText: finding.clause_text || undefined,
                              });
                            });
                          }}
                            className="flex items-center gap-1 px-2.5 py-1 text-[9px] font-medium rounded bg-cyan-600 text-white hover:bg-cyan-700 border border-cyan-700 transition-colors shadow-sm">
                            <ExternalLink className="w-3 h-3" /> Locate Clause
                          </button>

                          {/* Generate Redline */}
                          <button onClick={() => generateRedlineMutation.mutate(finding)}
                            disabled={generateRedlineMutation.isPending}
                            className="flex items-center gap-1 px-2.5 py-1 text-[9px] font-medium rounded bg-purple-600 text-white hover:bg-purple-700 border border-purple-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed">
                            {generateRedlineMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                            {generateRedlineMutation.isPending ? "Generating..." : "Generate Redline"}
                          </button>

                          {/* Spacer */}
                          <div className="flex-1" />

                          {/* Resolve */}
                          <button onClick={() => handleResolve(finding.finding_id)}
                            className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-green-600 text-white hover:bg-green-700 border border-green-700 transition-colors shadow-sm">
                            <CheckCircle2 className="w-3 h-3" /> Resolve
                          </button>

                          {/* Escalate */}
                          <button onClick={() => handleResolve(finding.finding_id)}
                            className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-red-100 text-red-700 hover:bg-red-200 border border-red-200 transition-colors">
                            <AlertTriangle className="w-3 h-3" /> Escalate
                          </button>
                          {/* Waive */}
                          <button onClick={() => handleResolve(finding.finding_id)}
                            className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-amber-100 text-amber-700 hover:bg-amber-200 border border-amber-200 transition-colors">
                            <XCircle className="w-3 h-3" /> Waive
                          </button>
                          {/* Dismiss */}
                          <button className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200 transition-colors">
                            <XCircle className="w-3 h-3" /> Dismiss
                          </button>
                        </div>
                      )}
                    </div>
                    );
                  })()}
                </div>
              );
            })}
          </div>
        )}

        {/* Severity Color Legend */}
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-50 dark:bg-navy-750 border border-gray-100 dark:border-navy-700">
          <span className="text-[7px] font-semibold text-gray-500 uppercase">Legend</span>
          <span className="flex items-center gap-1 text-[8px] text-red-600"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> Critical</span>
          <span className="flex items-center gap-1 text-[8px] text-red-500"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> High</span>
          <span className="flex items-center gap-1 text-[8px] text-amber-700"><span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> Medium</span>
          <span className="flex items-center gap-1 text-[8px] text-gray-500"><span className="w-2 h-2 rounded-full bg-gray-400 inline-block" /> Low</span>
        </div>
      </div>
    </div>
  );
}

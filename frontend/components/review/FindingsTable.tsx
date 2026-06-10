/**
 * Findings Table — core review surface for AI-discovered risks.
 *
 * Features:
 * - Severity-coded rows (critical=red, high=orange, medium=amber, low=gray)
 * - Sortable columns
 * - Filtering by severity, clause type, resolution status
 * - Pagination
 * - Inline resolve/dismiss actions (disabled when review is immutable)
 * - Expandable rows for full description + recommendation + evidence
 */

"use client";

import React, { useState, useCallback, useEffect } from "react";
import {
  AlertTriangle, ChevronDown, ChevronUp, CheckCircle2, XCircle, Lock,
  Filter, ArrowUpDown, Search, BookOpen,
} from "lucide-react";
import type { FindingItem, ReviewDetail } from "@/services/api/client";
import { useReviewFindings, useResolveFinding, useReview, useRiskBreakdown } from "@/services/hooks";
import type { MitigatedFinding } from "@/services/api/client";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { TableSkeleton } from "@/components/shared/LoadingSkeleton";
import { isImmutable, getAllowedActions } from "@/lib/workflow";

interface FindingsTableProps {
  reviewId: string;
  onFindingSelect?: (sourceLocation: FindingItem["source_location"]) => void;
  review?: ReviewDetail | null;
}

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

const SEVERITY_STYLES: Record<string, { bg: string; dot: string; label: string }> = {
  critical: {
    bg: "bg-red-50 border-red-200 dark:bg-red-900/10 dark:border-red-800",
    dot: "bg-red-500",
    label: "text-red-700 dark:text-red-300",
  },
  high: {
    bg: "bg-orange-50 border-orange-200 dark:bg-orange-900/10 dark:border-orange-800",
    dot: "bg-orange-500",
    label: "text-orange-700 dark:text-orange-300",
  },
  medium: {
    bg: "bg-amber-50 border-amber-200 dark:bg-amber-900/10 dark:border-amber-800",
    dot: "bg-amber-500",
    label: "text-amber-700 dark:text-amber-300",
  },
  low: {
    bg: "bg-gray-50 border-gray-200 dark:bg-gray-800 dark:border-gray-700",
    dot: "bg-gray-400",
    label: "text-gray-600 dark:text-gray-400",
  },
  info: {
    bg: "bg-blue-50 border-blue-200 dark:bg-blue-900/10 dark:border-blue-800",
    dot: "bg-blue-400",
    label: "text-blue-700 dark:text-blue-300",
  },
};

function confidencePercent(value: number | null | undefined) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function SourceLocationPanel({ finding }: { finding: FindingItem }) {
  const source = finding.source_location;
  if (!source) {
    return (
      <div className="mb-3 ml-7 rounded-lg border border-gray-200 bg-white/70 p-3 text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-800/60 dark:text-gray-400">
        Source location unavailable. Finding generated from document-level analysis.
      </div>
    );
  }

  return (
    <div className="mb-3 ml-7 rounded-lg border border-blue-200 bg-white/80 p-3 dark:border-blue-800 dark:bg-gray-800/70">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">
        Source Location
      </p>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-300 sm:grid-cols-4">
        <span>Page: <span className="font-semibold">{source.page_number ?? "—"}</span></span>
        <span>Section: <span className="font-semibold">{source.section_heading || "—"}</span></span>
        <span>Paragraph: <span className="font-semibold">{source.paragraph_index ?? "—"}</span></span>
        <span>Confidence: <span className="font-semibold">{confidencePercent(source.confidence_score)}</span></span>
      </div>
    </div>
  );
}

function TraceabilityChain({ finding }: { finding: FindingItem }) {
  const source = finding.source_location?.source_text;
  return (
    <div className="mb-3 ml-7 rounded-lg border border-gray-200 bg-white/80 p-3 dark:border-gray-700 dark:bg-gray-800/70">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        Traceability Chain
      </p>
      <div className="mt-2 space-y-1.5 text-xs text-gray-700 dark:text-gray-300">
        <p><span className="font-semibold">Source Clause:</span> {source ? `${source.slice(0, 220)}${source.length > 220 ? "..." : ""}` : "Document-level analysis"}</p>
        <p className="text-gray-400">↓</p>
        <p><span className="font-semibold">AI Finding:</span> {finding.title}</p>
        <p className="text-gray-400">↓</p>
        <p><span className="font-semibold">Policy Match:</span> {finding.clause_type?.replace(/_/g, " ") || "Review policy"}</p>
        <p className="text-gray-400">↓</p>
        <p><span className="font-semibold">Generated Redline:</span> {finding.recommendation || "Recommendation pending"}</p>
      </div>
    </div>
  );
}

export function FindingsTable({ reviewId, onFindingSelect, review }: FindingsTableProps) {
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [resolutionFilter, setResolutionFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sortField, setSortField] = useState<"severity" | "confidence" | "clause_type">("severity");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  // Fetch review if not provided
  const reviewQuery = useReview(reviewId);
  const currentReview = review ?? reviewQuery.data;
  const actions = currentReview ? getAllowedActions(currentReview.status) : null;
  const immutable = currentReview ? isImmutable(currentReview.status) : false;

  const [resolveError, setResolveError] = useState<string | null>(null);

  const findingsQuery = useReviewFindings(reviewId, {
    severity: severityFilter || undefined,
    resolution: resolutionFilter || undefined,
    page,
    page_size: 20,
  });

  const resolveMutation = useResolveFinding(reviewId);
  const riskQuery = useRiskBreakdown(reviewId);
  const exposureByFindingId = React.useMemo(() => {
    const map = new Map<string, MitigatedFinding>();
    const all = [
      ...(riskQuery.data?.open_findings ?? []),
      ...(riskQuery.data?.mitigated_findings ?? []),
      ...(riskQuery.data?.accepted_risk_findings ?? []),
      ...(riskQuery.data?.dismissed_findings ?? []),
    ];
    for (const item of all) {
      if (item.finding_id) map.set(item.finding_id, item);
    }
    return map;
  }, [riskQuery.data]);

  const findings = findingsQuery.data?.findings ?? [];
  const total = findingsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  const handleResolve = async (findingId: string, resolution: string) => {
    setResolveError(null);
    try {
      await resolveMutation.mutateAsync({
        findingId,
        body: { resolution: resolution as any, note: "" },
      });
    } catch (e: any) {
      setResolveError(e?.message || "Failed to resolve finding. It may have been already resolved.");
    }
  };

  const toggleSort = (field: string) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field as any);
      setSortDir("desc");
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      {/* Header */}
      <div className="border-b border-gray-100 px-5 py-4 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Findings ({total})
          </h2>
          <div className="flex items-center gap-2">
            {/* Severity filter */}
            <select
              value={severityFilter}
              onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
            {/* Resolution filter */}
            <select
              value={resolutionFilter}
              onChange={(e) => { setResolutionFilter(e.target.value); setPage(1); }}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              <option value="">All Status</option>
              <option value="open">Open</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
              <option value="false_positive">False Positive</option>
            </select>
          </div>
        </div>
      </div>

      {/* Body */}
      <AsyncBoundary
        isLoading={findingsQuery.isLoading}
        error={findingsQuery.error}
        isEmpty={findings.length === 0}
        loadingSkeleton={<TableSkeleton rows={5} columns={5} />}
        emptyMessage="No findings"
        emptyDescription="AI analysis did not identify any risks in this contract."
        onRetry={() => findingsQuery.refetch()}
      >
        {resolveError && (
          <div className="mx-5 mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
            {resolveError}
          </div>
        )}
        <div className="divide-y divide-gray-100 dark:divide-gray-700">
          {findings.map((finding) => {
            const styles = SEVERITY_STYLES[finding.severity] || SEVERITY_STYLES.info;
            const isExpanded = expandedId === finding.finding_id;

            return (
              <div key={finding.finding_id} className={`${styles.bg} border-l-2 ${
                finding.severity === "critical" ? "border-l-red-500"
                : finding.severity === "high" ? "border-l-orange-500"
                : finding.severity === "medium" ? "border-l-amber-500"
                : "border-l-transparent"
              }`}>
                {/* Main row */}
                <div
                  className="flex cursor-pointer items-center gap-3 px-5 py-3"
                  onClick={() => setExpandedId(isExpanded ? null : finding.finding_id)}
                >
                  {/* Severity dot */}
                  <span className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${styles.dot}`} />

                  {/* Severity badge */}
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles.label} ${styles.bg}`}>
                    {finding.severity}
                  </span>

                  {/* Title */}
                  <span className="flex-1 truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                    {finding.title}
                  </span>

                  {/* Clause type */}
                  {finding.clause_type && (
                    <span className="hidden text-xs text-gray-500 dark:text-gray-400 sm:inline">
                      {finding.clause_type.replace(/_/g, " ")}
                    </span>
                  )}

                  {/* Confidence */}
                  {finding.confidence != null && (
                    <span className="hidden text-xs text-gray-400 dark:text-gray-500 lg:inline">
                      {Math.round(finding.confidence * 100)}%
                    </span>
                  )}

                  {/* Resolution badge */}
                  {finding.resolution ? (
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                      finding.resolution === "resolved" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : finding.resolution === "dismissed" || finding.resolution === "false_positive" ? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                      : finding.resolution === "acknowledged" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
                      : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    }`}>
                      <CheckCircle2 className="h-3 w-3" />
                      {finding.resolution.replace(/_/g, " ")}
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
                      Open
                    </span>
                  )}

                  {/* Expand toggle */}
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
                </div>

                {/* Expanded detail — Finding → Mitigation chain */}
                {isExpanded && (
                  <div className="border-t border-gray-100 px-5 py-4 dark:border-gray-700">
                    {/* Step 1: Finding description */}
                    <div className="mb-3 flex items-start gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-[9px] font-bold text-red-700 dark:bg-red-900/30 dark:text-red-400">1</span>
                      <div className="flex-1">
                        <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Finding</p>
                        <p className="mt-0.5 text-sm leading-relaxed text-gray-600 dark:text-gray-400">
                          {finding.description}
                        </p>
                      </div>
                    </div>

                    {(finding.playbook_id || finding.rule_id) && (
                      <div className="mb-3 ml-7 rounded-lg border border-indigo-200 bg-indigo-50/50 p-3 dark:border-indigo-800 dark:bg-indigo-900/10">
                        <p className="text-[10px] font-semibold text-indigo-700 dark:text-indigo-300 uppercase tracking-wide flex items-center gap-1">
                          <BookOpen className="h-3 w-3" /> Policy Linkage
                        </p>
                        <p className="mt-1 text-xs text-indigo-800 dark:text-indigo-200">
                          {finding.policy_rule_name || finding.policy_name || "Linked policy rule"}
                          {finding.policy_version ? ` · v${finding.policy_version}` : ""}
                        </p>
                        {finding.policy_owner && (
                          <p className="text-[10px] text-gray-500 mt-0.5">Owner: {finding.policy_owner}</p>
                        )}
                      </div>
                    )}

                    {/* Step 2: Business Impact */}
                    {exposureByFindingId.get(finding.finding_id)?.business_impact && (
                      <div className="mb-3 ml-7 rounded-lg border-l-2 border-red-300 bg-red-50/60 p-3 dark:border-red-700 dark:bg-red-900/10">
                        <p className="text-[10px] font-semibold text-red-700 dark:text-red-300 uppercase tracking-wide">Business Impact</p>
                        <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                          {exposureByFindingId.get(finding.finding_id)!.business_impact}
                        </p>
                      </div>
                    )}

                    {/* Step 3: Recommended Mitigation */}
                    {(exposureByFindingId.get(finding.finding_id)?.recommended_mitigation || finding.recommendation) && (
                      <div className="mb-3 ml-7 flex items-start gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-[9px] font-bold text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">2</span>
                        <div className="flex-1 rounded-lg border-l-2 border-blue-300 bg-blue-50 p-3 dark:border-blue-700 dark:bg-blue-900/10">
                          <p className="text-[10px] font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wide">Recommended Mitigation</p>
                          <p className="mt-1 text-sm text-blue-600 dark:text-blue-400">
                            {exposureByFindingId.get(finding.finding_id)?.recommended_mitigation || finding.recommendation}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Step 3b: Linked Redline (if any) */}
                    {exposureByFindingId.get(finding.finding_id)?.linked_redline_count ? (
                      <div className="mb-3 ml-14 flex items-start gap-2">
                        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-indigo-100 text-[8px] font-bold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">RL</span>
                        <div className="flex-1 rounded-lg border border-indigo-200 bg-indigo-50/60 p-2.5 dark:border-indigo-800 dark:bg-indigo-900/10">
                          <p className="text-[10px] font-semibold text-indigo-700 dark:text-indigo-300">
                            Linked Redline ({exposureByFindingId.get(finding.finding_id)!.linked_redline_count})
                          </p>
                          <p className="mt-0.5 text-xs text-indigo-600 dark:text-indigo-400">
                            {exposureByFindingId.get(finding.finding_id)!.review_state === "mitigated"
                              ? "Redline accepted — risk mitigated"
                              : "Redline proposed — pending review"}
                          </p>
                        </div>
                      </div>
                    ) : null}

                    {/* Step 4: Decision + Risk Delta */}
                    {finding.resolution && (
                      <div className="mb-3 ml-14 flex items-start gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-[9px] font-bold text-green-700 dark:bg-green-900/30 dark:text-green-400">3</span>
                        <div className="flex-1 rounded-lg border-l-2 border-green-300 bg-green-50 p-3 dark:border-green-700 dark:bg-green-900/10">
                          <p className="text-[10px] font-semibold text-green-700 dark:text-green-300 uppercase tracking-wide">Decision</p>
                          <div className="mt-1 flex items-center gap-2">
                            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                              {finding.resolution.replace(/_/g, " ")}
                            </span>
                            {exposureByFindingId.get(finding.finding_id)?.risk_reduction_value ? (
                              <span className="text-xs font-semibold text-green-600">
                                −{((exposureByFindingId.get(finding.finding_id)!.risk_reduction_value ?? 0) * 100).toFixed(0)}% exposure
                              </span>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Step 4b: Remaining exposure impact (if open) */}
                    {!finding.resolution && exposureByFindingId.get(finding.finding_id)?.remaining_contribution != null && (
                      <div className="mb-3 ml-14 flex items-start gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-100 text-[9px] font-bold text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">!</span>
                        <div className="flex-1 rounded-lg border-l-2 border-amber-300 bg-amber-50 p-3 dark:border-amber-700 dark:bg-amber-900/10">
                          <p className="text-[10px] font-semibold text-amber-700 dark:text-amber-300 uppercase tracking-wide">Open Exposure</p>
                          <p className="mt-1 text-sm font-semibold text-red-600">
                            +{((exposureByFindingId.get(finding.finding_id)!.remaining_contribution ?? 0) * 100).toFixed(0)}% remaining exposure
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Evidence: page numbers */}
                    <SourceLocationPanel finding={finding} />
                    <TraceabilityChain finding={finding} />

                    {/* View in contract button */}
                    {onFindingSelect && (
                      <div className="mb-3 ml-7">
                        <button
                          title="Navigate to the contract text that generated this finding."
                          onClick={(e) => {
                            e.stopPropagation();
                            onFindingSelect(finding.source_location ?? null);
                          }}
                          className="inline-flex items-center gap-1.5 rounded-md bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-800"
                        >
                          <BookOpen className="h-3.5 w-3.5" />
                          View Source Location
                        </button>
                      </div>
                    )}

                    {/* Resolution actions (only if not already resolved and mutable) */}
                    {!finding.resolution && actions?.canResolveFindings && (
                      <div className="ml-7 mt-4 border-t border-gray-100 pt-3 dark:border-gray-700">
                        <p className="mb-2 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Take Action</p>
                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={(e) => { e.stopPropagation(); handleResolve(finding.finding_id, "acknowledged"); }}
                            className="inline-flex items-center gap-1.5 rounded-md bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-800"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Acknowledge
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleResolve(finding.finding_id, "dismissed"); }}
                            className="inline-flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                          >
                            <XCircle className="h-3.5 w-3.5" />
                            Dismiss
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleResolve(finding.finding_id, "false_positive"); }}
                            className="inline-flex items-center gap-1.5 rounded-md bg-orange-100 px-3 py-1.5 text-xs font-medium text-orange-700 transition-colors hover:bg-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:hover:bg-orange-800"
                          >
                            <AlertTriangle className="h-3.5 w-3.5" />
                            False Positive
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Locked indicator for immutable reviews */}
                    {!finding.resolution && immutable && (
                      <div className="ml-7 flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-800">
                        <Lock className="h-3.5 w-3.5 text-gray-400" />
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          Findings are locked — review is in '{currentReview?.status?.replace(/_/g, " ")}' state
                        </span>
                      </div>
                    )}

                    {/* Resolution info */}
                    {finding.resolved_by && (
                      <div className="ml-7 mt-2 rounded-md bg-gray-50 p-2 text-xs text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                        Resolved by {finding.resolved_by}
                        {finding.resolved_at && <> on {new Date(finding.resolved_at).toLocaleDateString()}</>}
                        {finding.resolution_note && <> — {finding.resolution_note}</>}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </AsyncBoundary>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, total)} of {total}
          </p>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="rounded-md px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-400 dark:hover:bg-gray-700"
            >
              Previous
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const start = Math.max(1, Math.min(page - 2, totalPages - 4));
              const p = start + i;
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`rounded-md px-3 py-1 text-xs font-medium ${
                    p === page
                      ? "bg-blue-600 text-white"
                      : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
                  }`}
                >
                  {p}
                </button>
              );
            })}
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="rounded-md px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-400 dark:hover:bg-gray-700"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Loading overlay for mutations */}
      {resolveMutation.isPending && (
        <div className="border-t border-gray-100 px-5 py-2 text-center text-xs text-blue-600 dark:border-gray-700 dark:text-blue-400">
          Updating finding...
        </div>
      )}
    </div>
  );
}

// ── Immediate Attention Needed — enterprise priority queue ───────
// Ordering:
//   1. Unresolved criticals (severity=critical, resolution=open)
//   2. Rejected critical mitigations (redline rejected, finding critical)
//   3. Highest remaining exposure (descending remaining_contribution)
//   4. Aging/escalation (oldest unresolved first — uses finding order from backend)

interface FindingsNavigatorProps {
  reviewId: string;
  total: number;
}

export function FindingsNavigator({ reviewId, total }: FindingsNavigatorProps) {
  const [expanded, setExpanded] = useState(false);
  const findingsQuery = useReviewFindings(reviewId, { page_size: 100 });
  const riskQuery = useRiskBreakdown(reviewId);

  const findings = findingsQuery.data?.findings ?? [];
  const openExposures = riskQuery.data?.open_findings ?? [];
  const mitigatedFindings = riskQuery.data?.mitigated_findings ?? [];

  const criticalUnresolved = openExposures.filter((f) => f.severity === "critical").length;
  const highUnresolved = openExposures.filter((f) => f.severity === "high").length;
  const mediumUnresolved = openExposures.filter((f) => f.severity === "medium").length;
  const acceptedRisk = riskQuery.data?.accepted_risk_findings?.length ?? 0;
  const mitigated = mitigatedFindings.length;
  const dismissed = riskQuery.data?.dismissed_findings?.length ?? 0;

  // Build prioritized queue
  const priorityQueue = (() => {
    // 1. Unresolved criticals (highest priority)
    const unresolvedCriticals = openExposures.filter(f => f.severity === "critical");

    // 2. Rejected critical mitigations (findings that had redlines rejected)
    const rejectedMitigations = mitigatedFindings.filter(f =>
      f.severity === "critical" && f.review_state === "rejected"
    );

    // 3. All other open exposures sorted by highest remaining contribution
    const remainingOpen = openExposures
      .filter(f => f.severity !== "critical")
      .sort((a, b) => (b.remaining_contribution ?? 0) - (a.remaining_contribution ?? 0));

    // Combine with deduplication by finding_id
    const seen = new Set<string>();
    const combined: typeof openExposures = [];

    for (const item of [...unresolvedCriticals, ...rejectedMitigations, ...remainingOpen]) {
      const key = item.finding_id || item.title;
      if (!seen.has(key)) {
        seen.add(key);
        combined.push(item);
      }
    }

    return combined.slice(0, 8);
  })();

  return (
    <div className="sticky top-0 z-10 -mx-6 px-6 py-2 bg-white border-b border-gray-200 shadow-sm dark:bg-gray-800 dark:border-gray-700">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 text-xs"
      >
        <div className="flex items-center gap-2 font-semibold text-gray-700 dark:text-gray-300">
          {expanded ? "▾" : "▸"} Immediate Attention Needed
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {criticalUnresolved > 0 && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 text-[9px] font-semibold dark:bg-red-900/30 dark:text-red-400">
              {criticalUnresolved} critical
            </span>
          )}
          {highUnresolved > 0 && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700 text-[9px] font-semibold dark:bg-orange-900/30 dark:text-orange-400">
              {highUnresolved} high
            </span>
          )}
          {mediumUnresolved > 0 && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[9px] font-semibold dark:bg-amber-900/30 dark:text-amber-400">
              {mediumUnresolved} to review
            </span>
          )}
          {mitigated > 0 && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-[9px] font-semibold dark:bg-green-900/30 dark:text-green-400">
              {mitigated} mitigated
            </span>
          )}
          {acceptedRisk > 0 && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-orange-50 text-orange-600 text-[9px] font-semibold dark:bg-orange-900/10 dark:text-orange-400">
              {acceptedRisk} accepted
            </span>
          )}
          {dismissed > 0 && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[9px] font-semibold dark:bg-gray-700 dark:text-gray-400">
              {dismissed} dismissed
            </span>
          )}
          <span className="text-gray-400 text-[9px]">({total} total)</span>
        </div>
      </button>

      {/* Expanded quick-scan list: prioritized queue */}
      {expanded && priorityQueue.length > 0 && (
        <div className="mt-2 space-y-1 pb-1">
          {priorityQueue.map((f, idx) => (
            <div key={f.finding_id || f.title} className="flex items-center gap-2 px-2 py-1 rounded text-[10px] hover:bg-gray-50 dark:hover:bg-gray-700/30">
              {/* Priority rank indicator */}
              <span className={`w-4 text-center text-[8px] font-bold flex-shrink-0 ${
                idx < criticalUnresolved ? "text-red-500" :
                idx < criticalUnresolved + 1 ? "text-orange-500" :
                "text-gray-400"
              }`}>
                {idx + 1}.
              </span>
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                f.severity === "critical" ? "bg-red-500" :
                f.severity === "high" ? "bg-orange-500" :
                f.severity === "medium" ? "bg-amber-500" : "bg-blue-400"
              }`} />
              <span className="flex-1 truncate text-gray-700 dark:text-gray-300">{f.title}</span>
              {f.business_impact && (
                <span className="hidden lg:block text-[8px] text-gray-400 truncate max-w-[120px]">
                  {f.business_impact}
                </span>
              )}
              {f.remaining_contribution != null && f.remaining_contribution > 0 && (
                <span className="text-[8px] font-bold text-red-600">+{(f.remaining_contribution * 100).toFixed(0)}%</span>
              )}
              <span className="text-[8px] font-semibold px-1 py-0.5 rounded-full flex-shrink-0 text-gray-500 bg-gray-100 dark:bg-gray-700 dark:text-gray-400">
                {f.severity}
              </span>
            </div>
          ))}
          {openExposures.length > 8 && (
            <p className="text-[9px] text-gray-400 px-2 pt-1">
              +{openExposures.length - 8} more in priority queue
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Findings Navigation Bar ──────────────────────────────────────────

interface FindingsNavigationBarProps {
  findings: FindingItem[];
  currentIndex: number;
  onNavigate: (index: number) => void;
}

export function FindingsNavigationBar({ findings, currentIndex, onNavigate }: FindingsNavigationBarProps) {
  const total = findings.length;
  const current = currentIndex + 1;

  const goNext = useCallback(() => {
    if (currentIndex < total - 1) onNavigate(currentIndex + 1);
  }, [currentIndex, total, onNavigate]);

  const goPrev = useCallback(() => {
    if (currentIndex > 0) onNavigate(currentIndex - 1);
  }, [currentIndex, onNavigate]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Only handle when not typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        goNext();
      } else if (e.key === "p" || e.key === "P") {
        e.preventDefault();
        goPrev();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goNext, goPrev]);

  if (total === 0) return null;

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-white border-b border-gray-200 dark:bg-gray-800 dark:border-gray-700">
      <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
        Finding {current} of {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={goPrev}
          disabled={currentIndex <= 0}
          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed dark:text-gray-300 dark:hover:bg-gray-700"
          title="Previous (P)"
        >
          ◀ Prev
        </button>
        <button
          onClick={goNext}
          disabled={currentIndex >= total - 1}
          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed dark:text-gray-300 dark:hover:bg-gray-700"
          title="Next (N)"
        >
          Next ▶
        </button>
      </div>
      <div className="ml-2 flex items-center gap-1">
        <span className="text-[10px] text-gray-400">Jump to:</span>
        <select
          value={currentIndex}
          onChange={(e) => onNavigate(Number(e.target.value))}
          className="rounded border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
        >
          {findings.map((f, i) => (
            <option key={f.finding_id || i} value={i}>
              #{i + 1} - {f.severity.toUpperCase()} - {f.title?.slice(0, 40)}
            </option>
          ))}
        </select>
      </div>
      <div className="ml-auto text-[10px] text-gray-400">
        <kbd className="rounded border border-gray-300 bg-gray-100 px-1 py-0.5 font-mono text-[9px] dark:border-gray-600 dark:bg-gray-700">N</kbd> next{' '}
        <kbd className="rounded border border-gray-300 bg-gray-100 px-1 py-0.5 font-mono text-[9px] dark:border-gray-600 dark:bg-gray-700">P</kbd> prev
      </div>
    </div>
  );
}

/**
 * Redlines Panel — AI-suggested contract clause replacements.
 *
 * Uses the new collapsible RedlineCard with:
 * - Compact summary headers
 * - Risk-based grouping
 * - Operation badges
 * - Business impact display
 * - Expandable detail
 */

"use client";

import React, { useState, useMemo } from "react";
import { FileEdit, CheckCircle2, XCircle, Edit3, BookOpen, Lock, AlertTriangle, TrendingDown, Shield } from "lucide-react";
import type { RedlineItem, ReviewDetail, ConfidenceLabel, LocatorResponse, RiskTraceability } from "@/services/api/client";
import { useReviewRedlines, useUpdateRedline, useReview } from "@/services/hooks";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";
import { RedlineEditModal } from "./RedlineEditModal";
import { RedlineCard, RiskGroupHeader } from "./RedlineCard";
import { AnimatePresence } from "framer-motion";
import { isImmutable, getAllowedActions } from "@/lib/workflow";

// ── Confidence label helpers ──────────────────────────────────────

function numericToLabel(confidence: number): ConfidenceLabel {
  if (confidence >= 0.90) return { label: "Very High", tier: "very_high", numeric: confidence };
  if (confidence >= 0.75) return { label: "High", tier: "high", numeric: confidence };
  if (confidence >= 0.55) return { label: "Medium", tier: "medium", numeric: confidence };
  if (confidence >= 0.35) return { label: "Low", tier: "low", numeric: confidence };
  return { label: "Uncertain", tier: "uncertain", numeric: confidence };
}

const CONFIDENCE_TIER_COLORS: Record<string, string> = {
  very_high: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  high:      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  medium:    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  low:       "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  uncertain: "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400",
};

function ConfidencePill({ label }: { label: ConfidenceLabel }) {
  const colorClass = CONFIDENCE_TIER_COLORS[label.tier] ?? CONFIDENCE_TIER_COLORS.uncertain;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${colorClass}`}>
      Placement confidence: {label.label}
    </span>
  );
}

// ── Insertion marker — shows WHERE the clause will be inserted ────

function InsertionMarker({ locator }: { locator: LocatorResponse }) {
  if (!locator?.section_title && !locator?.reason) return null;

  const position = locator.insert_position || "after_section";
  const section = locator.section_title;
  const isAfter = position === "after_section";
  const isBefore = position === "before_section";
  const isWithin = position === "within_section";

  let markerText = locator.reason || "";
  if (!markerText && section) {
    if (isWithin) markerText = `Within the "${section}" section`;
    else if (isBefore) markerText = `Before the "${section}" section`;
    else markerText = `After the "${section}" section`;
  }

  return (
    <div className="mb-3 rounded-lg border border-blue-200 bg-blue-50/60 px-3 py-2 dark:border-blue-800 dark:bg-blue-900/10">
      <div className="flex items-start gap-2">
        <div className="mt-0.5 flex-shrink-0 w-3 h-3 rounded-full bg-blue-500 ring-2 ring-blue-200 dark:ring-blue-800" />
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
            Insertion point
          </p>
          <p className="mt-0.5 text-xs text-blue-700 dark:text-blue-300">{markerText}</p>
        </div>
      </div>
      {section && (
        <div className="mt-2 ml-5 border-l-2 border-blue-300 pl-3 dark:border-blue-700">
          <div className="flex items-center gap-1.5 text-[10px] text-blue-500 dark:text-blue-400">
            <span className="font-mono">▼ INSERT HERE</span>
          </div>
          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
            {isAfter ? `↪ ${section}` : isBefore ? `${section} ↩` : `◦ ${section}`}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Risk Traceability Chain ────────────────────────────────────────

function RiskTraceabilityChain({ traceability }: { traceability: RiskTraceability }) {
  const { detected_risk, business_impact, mitigation_strategy,
          mitigation_type, estimated_reduction_pct, confidence, source, generated_from } = traceability;
  if (!detected_risk && !business_impact && !mitigation_strategy) return null;

  // Determine if this is a mitigation-generated redline
  const isMitigationGenerated = generated_from === "mitigation_recommendation";

  return (
    <div className={`mt-3 rounded-lg border p-3 ${
      isMitigationGenerated
        ? "border-emerald-200 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-900/10"
        : "border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-900/10"
    }`}>
      <p className={`mb-2 text-[10px] font-semibold uppercase tracking-wider ${
        isMitigationGenerated
          ? "text-emerald-600 dark:text-emerald-400"
          : "text-amber-600 dark:text-amber-400"
      }`}>
        {isMitigationGenerated ? "Generated from Mitigation" : "Risk Analysis"}
      </p>
      <div className="space-y-2">
        {detected_risk && (
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-amber-500" />
            <div>
              <p className="text-[10px] font-semibold text-amber-700 dark:text-amber-400">Detected Risk</p>
              <p className="text-xs text-gray-700 dark:text-gray-300">{detected_risk}</p>
            </div>
          </div>
        )}
        {business_impact && (
          <div className="flex items-start gap-2">
            <TrendingDown className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-red-400" />
            <div>
              <p className="text-[10px] font-semibold text-red-600 dark:text-red-400">Business Impact</p>
              <p className="text-xs text-gray-700 dark:text-gray-300">{business_impact}</p>
            </div>
          </div>
        )}
        {mitigation_strategy && (
          <div className="flex items-start gap-2">
            <Shield className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-500" />
            <div>
              <p className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">Mitigation Strategy</p>
              <p className="text-xs text-gray-700 dark:text-gray-300">{mitigation_strategy}</p>
            </div>
          </div>
        )}

        {/* Extended traceability — shown only for mitigation-generated redlines */}
        {isMitigationGenerated && (
          <div className="mt-2 space-y-1.5 border-t border-emerald-200 pt-2 dark:border-emerald-700">
            {mitigation_type && (
              <div className="flex items-start gap-2">
                <FileEdit className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-500" />
                <div>
                  <p className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">Mitigation Type</p>
                  <p className="text-xs text-gray-700 dark:text-gray-300">{mitigation_type.replace(/_/g, " ")}</p>
                </div>
              </div>
            )}
            {estimated_reduction_pct != null && (
              <div className="flex items-start gap-2">
                <TrendingDown className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-green-500" />
                <div>
                  <p className="text-[10px] font-semibold text-green-600 dark:text-green-400">Estimated Reduction</p>
                  <p className="text-xs font-semibold text-green-700 dark:text-green-300">
                    −{Math.round(estimated_reduction_pct * 100)}%
                  </p>
                </div>
              </div>
            )}
            {confidence != null && (
              <div className="flex items-start gap-2">
                <Shield className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-indigo-500" />
                <div>
                  <p className="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400">Confidence</p>
                  <p className="text-xs text-gray-700 dark:text-gray-300">
                    {Math.round(confidence * 100)}% · {source?.replace(/_/g, " ") || "unknown"}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Panel ─────────────────────────────────────────────────────────

interface RedlinesPanelProps {
  reviewId: string;
  review?: ReviewDetail | null;
  onRedlineSelect?: (redline: RedlineItem) => void;
}

export function RedlinesPanel({ reviewId, onRedlineSelect, review }: RedlinesPanelProps) {
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [editTarget, setEditTarget] = useState<any>(null);
  const [versionNotice, setVersionNotice] = useState<string | null>(null);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);
  const [expandedAll, setExpandedAll] = useState<"all" | "critical" | "none">("none");

  // Fetch review if not provided
  const reviewQuery = useReview(reviewId);
  const currentReview = review ?? reviewQuery.data;
  const actions = currentReview ? getAllowedActions(currentReview.status) : null;
  const immutable = currentReview ? isImmutable(currentReview.status) : false;

  const redlinesQuery = useReviewRedlines(reviewId, filterStatus || undefined);
  const updateMutation = useUpdateRedline(reviewId);

  const redlines = redlinesQuery.data?.redlines ?? [];

  const handleAccept = async (redlineId: string, reviewNotes?: string) => {
    setVersionNotice(null);
    setErrorNotice(null);
    try {
      const result = await updateMutation.mutateAsync({
        redlineId,
        body: { status: "accepted" as any, review_notes: reviewNotes },
      }) as any;
      if (result?.document_version?.version_number) {
        setVersionNotice(`Document v${result.document_version.version_number} saved. See Versions tab.`);
      }
    } catch (e: any) {
      setErrorNotice(e?.message || "Failed to accept redline. It may have been already resolved.");
    }
    setEditTarget(null);
  };

  const handleModify = async (redlineId: string, modifiedText: string, reviewNotes?: string) => {
    setVersionNotice(null);
    setErrorNotice(null);
    try {
      const result = await updateMutation.mutateAsync({
        redlineId,
        body: { status: "modified" as any, modified_text: modifiedText, review_notes: reviewNotes },
      }) as any;
      if (result?.document_version?.version_number) {
        setVersionNotice(`Document v${result.document_version.version_number} saved with custom text. See Versions tab.`);
      }
    } catch (e: any) {
      setErrorNotice(e?.message || "Failed to modify redline. It may have been already resolved.");
    }
    setEditTarget(null);
  };

  const handleReject = async (redlineId: string, reviewNotes?: string) => {
    setErrorNotice(null);
    try {
      await updateMutation.mutateAsync({
        redlineId,
        body: { status: "rejected" as any, review_notes: reviewNotes },
      });
    } catch (e: any) {
      setErrorNotice(e?.message || "Failed to reject redline. It may have been already resolved.");
    }
    setEditTarget(null);
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      proposed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
      accepted: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
      rejected: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
      modified: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
      superseded: "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400",
      needs_legal_review: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
      customer_requested: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
      fallback_language: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
    };
    return colors[status] || colors.proposed;
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      {/* Header */}
      <div className="border-b border-gray-100 px-5 py-4 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileEdit className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Redline Suggestions ({redlines.length})
            </h2>
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
          >
            <option value="">All</option>
            <option value="proposed">Proposed</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
            <option value="modified">Modified</option>
            <option value="needs_legal_review">Needs Legal Review</option>
            <option value="customer_requested">Customer Requested</option>
            <option value="fallback_language">Fallback Language</option>
          </select>
        </div>
        {/* Review Progress */}
        {(() => {
          const total = redlines.length;
          const accepted = redlines.filter(r => r.status === "accepted").length;
          const rejected = redlines.filter(r => r.status === "rejected").length;
          const modified = redlines.filter(r => r.status === "modified").length;
          const reviewed = accepted + rejected + modified;
          const pending = total - reviewed;
          const pct = total > 0 ? Math.round((reviewed / total) * 100) : 0;
          return (
            <div className="mt-3 flex items-center gap-4 text-[11px]">
              <div className="flex items-center gap-2 flex-1">
                <div className="h-1.5 flex-1 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                  <div className="h-full rounded-full bg-emerald-500 transition-all duration-500" style={{ width: `${pct}%` }} />
                </div>
                <span className="text-gray-500 dark:text-gray-400 font-medium whitespace-nowrap">{reviewed}/{total} reviewed</span>
              </div>
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">{accepted} accepted</span>
              <span className="text-red-600 dark:text-red-400 font-medium">{rejected} rejected</span>
              <span className="text-purple-600 dark:text-purple-400 font-medium">{modified} modified</span>
              {pending > 0 && <span className="text-gray-500 dark:text-gray-400">{pending} pending</span>}
            </div>
          );
        })()}
        {/* Expand/Collapse controls */}
        <div className="mt-2 flex items-center gap-2">
          <button onClick={() => setExpandedAll(expandedAll === "all" ? "none" : "all")} className={`text-[10px] font-medium px-2 py-1 rounded transition-colors ${expandedAll === "all" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"}`}>
            {expandedAll === "all" ? "▾ Collapse all" : "▸ Expand all"}
          </button>
          <button onClick={() => setExpandedAll(expandedAll === "critical" ? "none" : "critical")} className={`text-[10px] font-medium px-2 py-1 rounded transition-colors ${expandedAll === "critical" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"}`}>
            {expandedAll === "critical" ? "▾ Collapse critical" : "▸ Expand critical"}
          </button>
          <button onClick={() => setFilterStatus("proposed")} className="text-[10px] font-medium px-2 py-1 rounded text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">
            Pending only
          </button>
          {filterStatus && (
            <button onClick={() => setFilterStatus("")} className="text-[10px] font-medium px-2 py-1 rounded text-blue-500 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20">
              Clear filter
            </button>
          )}
        </div>
      </div>

      {versionNotice && (
        <div className="mx-5 mt-3 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-800 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300">
          {versionNotice}
        </div>
      )}
      {errorNotice && (
        <div className="mx-5 mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {errorNotice}
        </div>
      )}

      {/* Body: grouped collapsible cards */}
      <AsyncBoundary
        isLoading={redlinesQuery.isLoading}
        error={redlinesQuery.error}
        isEmpty={redlines.length === 0}
        loadingSkeleton={<CardSkeleton count={2} />}
        emptyMessage="No redline suggestions"
        emptyDescription={
          (currentReview?.finding_count ?? 0) > 0
            ? "Findings were identified but no clause edits were generated. Use Re-analyze to regenerate redlines (medium/high/critical findings)."
            : "AI did not suggest any clause changes for this contract."
        }
        onRetry={() => redlinesQuery.refetch()}
      >
        {(() => {
          // Group redlines by group_key (from locator) or risk_level
          const groups = new Map<string, RedlineItem[]>();
          for (const r of redlines) {
            const key = r.locator?.group_key || r.risk_level?.toLowerCase() || "other";
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key)!.push(r);
          }

          // Sort groups: critical/high first, then by name
          const groupOrder = ["financial", "litigation", "privacy", "compliance", "vendor_lockin", "ip_loss", "security", "operational", "reputational", "critical", "high", "medium", "low", "other"];
          const sortedGroups = Array.from(groups.entries()).sort((a, b) => {
            const ai = groupOrder.indexOf(a[0]);
            const bi = groupOrder.indexOf(b[0]);
            return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
          });

          return (
            <div className="space-y-4 p-4">
              {sortedGroups.map(([groupKey, items]) => (
                <div key={groupKey}>
                  <RiskGroupHeader groupKey={groupKey} count={items.length} />
                  <div className="space-y-2">
                    {items.map((redline) => (
                      <RedlineCard
                        key={redline.redline_id}
                        redline={redline}
                        onLocate={onRedlineSelect ? () => onRedlineSelect(redline) : undefined}
                        onAccept={handleAccept}
                        onReject={handleReject}
                        onEdit={setEditTarget}
                        immutable={immutable}
                        defaultExpanded={
                          expandedAll === "all" ? true :
                          expandedAll === "critical" ? (redline.risk_level?.toLowerCase() === "critical") :
                          false
                        }
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          );
        })()}
      </AsyncBoundary>

      {/* Edit Modal */}
      <AnimatePresence>
        {editTarget && (
          <RedlineEditModal
            redline={editTarget}
            onAccept={handleAccept}
            onModify={handleModify}
            onReject={handleReject}
            onClose={() => setEditTarget(null)}
            isLoading={updateMutation.isPending}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

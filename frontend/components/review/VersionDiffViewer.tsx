/**
 * VersionDiffViewer — word-level inline diff between document versions.
 *
 * Features:
 * - Word-level diff using backend difflib: only changed words highlighted
 * - Red background + strikethrough for deleted words
 * - Green background for inserted words
 * - Unchanged words shown normally
 * - Clause context with severity/status badges
 * - Filter by status and severity
 */

"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { FileText, Download, Loader2 } from "lucide-react";
import { reviewService } from "@/services/api/reviews";
import { computeSemanticDiff, LEGAL_DIFF_STYLES, type SemanticDiffSegment } from "@/lib/semanticDiff";

interface WordDiffSegment {
  tag: "equal" | "delete" | "insert";
  text: string;
}

interface DiffChange {
  type: string;
  operation?: string;
  clause_type: string;
  severity: string;
  status: string;
  rationale: string;
  confidence: number | null;
  anchor_text?: string;
  before: string;
  after: string;
  word_diff: WordDiffSegment[];
}

const OPERATION_LABELS: Record<string, string> = {
  insert: "New clause",
  modification: "Modification",
  replace: "Replacement",
  delete: "Deletion",
};

const OPERATION_COLORS: Record<string, string> = {
  insert: "bg-emerald-100 text-emerald-800",
  modification: "bg-blue-100 text-blue-700",
  replace: "bg-purple-100 text-purple-700",
  delete: "bg-red-100 text-red-700",
};

interface DiffResponse {
  version_a: { version_number: number; label: string | null };
  version_b: { version_number: number; label: string | null };
  changes: DiffChange[];
  total_changes: number;
}

interface DocumentVersion {
  version_id: string;
  version_number: number;
  label: string | null;
}

interface VersionDiffViewerProps {
  reviewId: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-green-100 text-green-700",
};

const STATUS_COLORS: Record<string, string> = {
  accepted: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  modified: "bg-blue-100 text-blue-700",
  proposed: "bg-gray-100 text-gray-600",
};

function InlineDiff({ segments }: { segments: SemanticDiffSegment[] }) {
  return (
    <p className="text-sm leading-relaxed whitespace-pre-wrap">
      {segments.map((seg, i) => {
        if (seg.tag === "delete") {
          return (
            <span key={i} className={LEGAL_DIFF_STYLES.delete}>
              {seg.text}
            </span>
          );
        }
        if (seg.tag === "insert") {
          return (
            <span key={i} className={LEGAL_DIFF_STYLES.insert}>
              {seg.text}
            </span>
          );
        }
        return <span key={i}>{seg.text}</span>;
      })}
    </p>
  );
}

function ClauseDiffRow({ change, isEven }: { change: DiffChange; isEven: boolean }) {
  const [expanded, setExpanded] = useState(true);
  const sevColor = SEVERITY_COLORS[change.severity] || SEVERITY_COLORS.medium;
  const statusColor = STATUS_COLORS[change.status] || STATUS_COLORS.proposed;
  const op = change.operation || change.type;
  const opColor = OPERATION_COLORS[op] || OPERATION_COLORS.modification;
  const opLabel = OPERATION_LABELS[op] || op;
  const isInsert = op === "insert";
  const segments = React.useMemo(
    () => computeSemanticDiff(isInsert ? "" : change.before, change.after),
    [change.after, change.before, isInsert],
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-lg border ${isEven ? "bg-white" : "bg-gray-50/50"}`}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-xs font-semibold text-gray-700 uppercase min-w-[100px]">
            {change.clause_type.replace(/_/g, " ")}
          </span>
          <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${sevColor}`}>
            {change.severity}
          </span>
          <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${statusColor}`}>
            {change.status}
          </span>
          <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${opColor}`}>
            {opLabel}
          </span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-gray-400">
          {change.confidence != null && (
            <span>{(change.confidence * 100).toFixed(0)}% confidence</span>
          )}
          <span className="text-gray-300">{expanded ? "\u25B2" : "\u25BC"}</span>
        </div>
      </button>

      {/* Inline Diff Content */}
      {expanded && segments.length > 0 && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          className="px-4 pb-4 space-y-2"
        >
          {isInsert && change.anchor_text && (
            <p className="text-[10px] text-gray-500 px-1">
              Insert after: <span className="font-medium text-gray-700">&ldquo;{change.anchor_text}&rdquo;</span>
            </p>
          )}
          <div className="rounded-lg border border-gray-200 bg-white p-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                {isInsert ? "New clause" : "Changes"}
              </span>
              <span className="text-[9px] text-gray-400">
                {isInsert
                  ? "(green = added; existing text preserved)"
                  : "(red = removed, green = added)"}
              </span>
            </div>
            <div className="p-3 bg-gray-50 rounded border border-gray-200">
              <InlineDiff segments={segments} />
            </div>
          </div>

          {/* Rationale */}
          {change.rationale && (
            <div className="px-3 py-2 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-[10px] font-semibold text-blue-700 mb-1">Rationale</p>
              <p className="text-xs text-blue-800">{change.rationale}</p>
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}

export function VersionDiffViewer({ reviewId }: VersionDiffViewerProps) {
  const [selectedV1, setSelectedV1] = useState<string>("");
  const [selectedV2, setSelectedV2] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const { data: versions } = useQuery<DocumentVersion[]>({
    queryKey: ["reviews", reviewId, "versions"],
    queryFn: () => reviewService.listVersions(reviewId),
    staleTime: 10_000,
  });

  const { data: diffData, isLoading: diffLoading } = useQuery<DiffResponse>({
    queryKey: ["reviews", reviewId, "diff", selectedV1, selectedV2],
    queryFn: () => reviewService.diffVersions(reviewId, selectedV1, selectedV2),
    enabled: !!selectedV1 && !!selectedV2,
    staleTime: 60_000,
  });

  const items = versions ?? [];

  const filteredChanges = (diffData?.changes ?? []).filter((c) => {
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    if (severityFilter !== "all" && c.severity !== severityFilter) return false;
    return true;
  });

  if (items.length < 2) {
    return (
      <div className="flex flex-col items-center py-12 text-center">
        <FileText className="w-10 h-10 text-gray-300 mb-3" />
        <p className="text-sm text-gray-500">Need at least 2 versions to compare</p>
        <p className="text-xs text-gray-400 mt-1">Accept redlines to generate v2 for comparison.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-700 mb-1">Original Version</label>
          <select value={selectedV1} onChange={(e) => setSelectedV1(e.target.value)}
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none">
            <option value="">Select...</option>
            {items.map((v) => (
              <option key={v.version_id} value={v.version_id}>v{v.version_number} — {v.label || `v${v.version_number}`}</option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-700 mb-1">Modified Version</label>
          <select value={selectedV2} onChange={(e) => setSelectedV2(e.target.value)}
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none">
            <option value="">Select...</option>
            {items.map((v) => (
              <option key={v.version_id} value={v.version_id}>v{v.version_number} — {v.label || `v${v.version_number}`}</option>
            ))}
          </select>
        </div>
      </div>

      {diffLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
        </div>
      )}

      {diffData && !diffLoading && (
        <>
          <div className="flex items-center justify-between p-3 bg-navy-900 text-white rounded-lg">
            <div className="flex items-center gap-4 text-xs">
              <span className="font-semibold">v{diffData.version_a.version_number} → v{diffData.version_b.version_number}</span>
              <span className="text-gray-300">|</span>
              <span>{diffData.total_changes} change(s)</span>
            </div>
            <div className="flex items-center gap-2">
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                className="text-[10px] bg-navy-800 text-white border border-navy-700 rounded px-2 py-1">
                <option value="all">All statuses</option>
                <option value="accepted">Accepted</option>
                <option value="rejected">Rejected</option>
                <option value="modified">Modified</option>
              </select>
              <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}
                className="text-[10px] bg-navy-800 text-white border border-navy-700 rounded px-2 py-1">
                <option value="all">All severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          {filteredChanges.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-sm">No changes match the current filters.</div>
          ) : (
            <div className="space-y-1">
              {filteredChanges.map((change, idx) => (
                <ClauseDiffRow key={idx} change={change} isEven={idx % 2 === 0} />
              ))}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            {[selectedV1, selectedV2].map((vid) => {
              const v = items.find((x) => x.version_id === vid);
              if (!v) return null;
              return (
                <a key={vid} href={`/api/v1/reviews/${reviewId}/versions/${vid}/download`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors">
                  <Download className="w-3 h-3" /> Download v{v.version_number}
                </a>
              );
            })}
          </div>
        </>
      )}

      {selectedV1 && selectedV2 && !diffData && !diffLoading && (
        <div className="text-center py-8 text-gray-500 text-sm">Select both versions above to see the diff.</div>
      )}
    </div>
  );
}

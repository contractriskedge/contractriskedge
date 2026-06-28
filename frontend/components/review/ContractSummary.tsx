/**
 * Contract Summary panel — top-level review metadata.
 *
 * Shows: file name, upload date, risk score, status, reviewer, version, AI run metadata.
 * For finalized reviews: shows immutable badge, finalized timestamp, approved by.
 */

"use client";

import React, { useState } from "react";
import { FileText, Calendar, User, Hash, Activity, Cpu, Clock, Lock, ShieldCheck, Download, Fingerprint, AlertTriangle } from "lucide-react";
import type { ReviewDetail, ReviewStatusResponse, AnalysisRunResponse, DocumentVersionItem } from "@/services/api/client";
import { reviewService } from "@/services/api/reviews";
import { useRiskBreakdown } from "@/services/hooks";
import { isImmutable, getStatusLabel, getStatusColor } from "@/lib/workflow";

interface ContractSummaryProps {
  review: ReviewDetail;
  status?: ReviewStatusResponse | null;
  analysisRun?: AnalysisRunResponse | null;
  /** Latest document version from Versions tab (distinct from review.version analysis counter). */
  documentVersionNumber?: number | null;
  documentVersionLabel?: string | null;
  /** Finalized version info for immutable display */
  finalizedVersion?: {
    version_id: string;
    version_number: number;
    checksum_sha256?: string | null;
    storage_key?: string | null;
  } | null;
}

export function ContractSummary({
  review,
  status,
  analysisRun,
  documentVersionNumber,
  documentVersionLabel,
  finalizedVersion,
}: ContractSummaryProps) {
  const [downloadingFinal, setDownloadingFinal] = useState(false);
  const { data: riskData } = useRiskBreakdown(review.review_id);
  const isRemainingMode = riskData?.exposure_mode === "remaining" || riskData?.review_started;
  const currentRisk = riskData?.current_contract_risk ?? riskData?.remaining_exposure;
  const originalRisk = review.risk_score ?? analysisRun?.risk_score ?? null;

  const severityColor = (score: number | null | undefined) => {
    if (!score) return "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
    if (score >= 0.7) return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    if (score >= 0.4) return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
  };

  const immutable = isImmutable(review.status);

  const handleDownloadFinal = async () => {
    if (!finalizedVersion?.version_id) return;
    setDownloadingFinal(true);
    try {
      await reviewService.downloadVersion(
        review.review_id,
        finalizedVersion.version_id,
        `contract_final_v${finalizedVersion.version_number}.docx`,
      );
    } catch {
      // User sees browser/network error from downloadFile
    } finally {
      setDownloadingFinal(false);
    }
  };

  const statusColor = (s: string) => {
    const colors: Record<string, string> = {
      draft: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300",
      ai_analyzed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
      under_review: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
      legal_review: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
      procurement_review: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
      security_review: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
      escalated: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
      approved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
      negotiation_sent: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
      executed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
      archived: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300",
    };
    return colors[s] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-100 px-5 py-4 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Contract Summary</h2>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-3 lg:grid-cols-4">
          {/* File name */}
          <div className="col-span-2 sm:col-span-3 lg:col-span-2">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <FileText className="h-4 w-4" />
              <span>Document</span>
            </div>
            <p className="mt-0.5 font-medium text-gray-900 dark:text-gray-100 truncate" title={review.document_name || review.review_id}>
              {review.document_name || review.original_filename || review.review_number || `Review ${review.review_id.slice(0, 8)}`}
            </p>
          </div>

          {/* Current Contract Risk — dominant live metric */}
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <AlertTriangle className="h-4 w-4" />
              <span>{isRemainingMode ? "Current Contract Risk" : "Detected Risk"}</span>
            </div>
            <span className={`mt-0.5 inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-bold ${severityColor(isRemainingMode ? currentRisk : originalRisk)}`}>
              {isRemainingMode && currentRisk != null
                ? `${(currentRisk * 100).toFixed(0)}%`
                : originalRisk != null
                  ? `${(originalRisk * 100).toFixed(0)}%`
                  : "—"}
            </span>
          </div>

          {/* Original AI Risk — immutable baseline (shown when in remaining mode) */}
          {isRemainingMode && originalRisk != null && (
            <div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Activity className="h-4 w-4" />
                <span>Original AI Risk</span>
              </div>
              <span className={`mt-0.5 inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-medium ${severityColor(originalRisk)}`}>
                {(originalRisk * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Status with immutable badge */}
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <Activity className="h-4 w-4" />
              <span>Status</span>
            </div>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-medium ${statusColor(review.status ?? "unknown")}`}>
                {(review.status ?? "unknown").replace(/_/g, " ")}
              </span>
              {immutable && (
                <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-600 dark:bg-amber-900/20 dark:text-amber-400">
                  <Lock className="h-3 w-3" />
                  Read Only
                </span>
              )}
            </div>
          </div>

          {/* Priority */}
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <AlertTriangle className="h-4 w-4" />
              <span>Priority</span>
            </div>
            <span className={`mt-0.5 inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-medium ${
              review.priority === "critical" ? "bg-red-100 text-red-700" :
              review.priority === "high" ? "bg-orange-100 text-orange-700" :
              review.priority === "medium" ? "bg-amber-100 text-amber-700" :
              "bg-gray-100 text-gray-600"
            }`}>
              {(review.priority ?? "normal").replace(/_/g, " ")}
            </span>
          </div>

          {/* Reviewer */}
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <User className="h-4 w-4" />
              <span>Reviewer</span>
            </div>
            <p className="mt-0.5 font-medium text-gray-900 dark:text-gray-100">
              {review.assigned_to || "Unassigned"}
            </p>
          </div>

          {/* Created By */}
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <User className="h-4 w-4" />
              <span>Created By</span>
            </div>
            <p className="mt-0.5 font-medium text-gray-900 dark:text-gray-100">
              {review.created_by || "—"}
            </p>
          </div>

          {/* Document version (v1 original, v2 after redlines) */}
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <Hash className="h-4 w-4" />
              <span>Doc version</span>
            </div>
            <p className="mt-0.5 font-medium text-gray-900 dark:text-gray-100">
              {documentVersionNumber
                ? `v${documentVersionNumber}${documentVersionLabel ? ` — ${documentVersionLabel}` : ""}`
                : `v${review.version ?? 1} (analysis)`}
            </p>
          </div>

          {/* Upload date */}
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <Calendar className="h-4 w-4" />
              <span>Uploaded</span>
            </div>
            <p className="mt-0.5 font-medium text-gray-900 dark:text-gray-100">
              {new Date(review.created_at).toLocaleDateString()}
            </p>
          </div>

          {/* AI Model */}
          {analysisRun && (
            <div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Cpu className="h-4 w-4" />
                <span>AI Model</span>
              </div>
              <p className="mt-0.5 font-medium text-gray-900 dark:text-gray-100">
                {analysisRun.model}
              </p>
            </div>
          )}

          {/* Analysis Duration */}
          {analysisRun?.latency_ms && (
            <div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Clock className="h-4 w-4" />
                <span>Analysis Time</span>
              </div>
              <p className="mt-0.5 font-medium text-gray-900 dark:text-gray-100">
                {(analysisRun.latency_ms / 1000).toFixed(1)}s
              </p>
            </div>
          )}

          {/* Token Usage */}
          {analysisRun?.total_tokens && analysisRun.total_tokens > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Cpu className="h-4 w-4" />
                <span>Tokens Used</span>
              </div>
              <p className="mt-0.5 font-medium text-gray-900 dark:text-gray-100">
                {analysisRun.total_tokens.toLocaleString()}
              </p>
            </div>
          )}

          {/* Finalized Contract Info — only for finalized/approved reviews */}
          {finalizedVersion && (
            <div className="col-span-full mt-2 rounded-lg border-2 border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-900/10">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-emerald-800 dark:text-emerald-300">
                      Final Approved Contract v{finalizedVersion.version_number}
                    </h4>
                    <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-400">
                      This document is the official final version. It is immutable and certified.
                    </p>
                    {finalizedVersion.checksum_sha256 && (
                      <div className="mt-2 flex items-center gap-1.5 text-[10px] text-emerald-600 dark:text-emerald-500">
                        <Fingerprint className="h-3 w-3" />
                        <span className="font-mono">SHA-256: {finalizedVersion.checksum_sha256.substring(0, 16)}...</span>
                      </div>
                    )}
                    {review.completed_at && (
                      <p className="mt-1 text-[10px] text-emerald-600 dark:text-emerald-500">
                        Finalized: {new Date(review.completed_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleDownloadFinal}
                  disabled={downloadingFinal || !finalizedVersion?.storage_key}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-medium text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
                >
                  <Download className="h-4 w-4" />
                  {downloadingFinal ? "Downloading…" : "Download Final"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Progress bar — shows review completion, NOT analysis completion */}
        {status && status.progress < 100 && (
          <div className="mt-4 space-y-1">
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span className="font-medium text-gray-600 dark:text-gray-300">Review Completion</span>
              <span>{status.progress}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
              <div
                className="h-full rounded-full bg-blue-500 transition-all duration-500"
                style={{ width: `${status.progress}%` }}
              />
            </div>
            <p className="text-[9px] text-gray-400">{status.current_step || "Processing..."}</p>
          </div>
        )}

        {/* Error state */}
        {status?.error && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
            {status.error}
          </div>
        )}
      </div>
    </div>
  );
}

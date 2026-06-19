"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  X,
  RotateCcw,
  Sparkles,
  FileSearch,
} from "lucide-react";
import type { BulkImportProgress } from "./bulkImportUtils";

interface BulkImportProgressBannerProps {
  progress: BulkImportProgress;
  onDismiss?: () => void;
  onRetryFailed?: () => void;
}

function StatPill({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "blue" | "purple" | "green" | "red";
}) {
  if (value <= 0) return null;

  const tones = {
    neutral: "bg-gray-100 text-gray-700 dark:bg-navy-700 dark:text-gray-200",
    blue: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    purple: "bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    green: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    red: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${tones[tone]}`}>
      <span className="tabular-nums font-semibold">{value}</span>
      <span>{label}</span>
    </span>
  );
}

export function BulkImportProgressBanner({
  progress,
  onDismiss,
  onRetryFailed,
}: BulkImportProgressBannerProps) {
  const {
    total,
    uploading,
    queued,
    processing,
    analyzing,
    completed,
    failed,
    active,
    percentComplete,
    isActive,
    aiQueuePending,
  } = progress;

  const allDone = !isActive && completed + failed >= total && total > 0;
  const hasFailures = failed > 0;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: "auto", opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        className={`mx-3 mb-2 rounded-xl border overflow-hidden shadow-sm ${
          allDone && !hasFailures
            ? "bg-green-50 border-green-200 dark:bg-green-900/15 dark:border-green-800/40"
            : hasFailures && !isActive
              ? "bg-amber-50 border-amber-200 dark:bg-amber-900/15 dark:border-amber-800/40"
              : "bg-white border-blue-200 dark:bg-navy-800 dark:border-blue-800/40"
        }`}
      >
        <div className="px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5 min-w-0 flex-1">
              <div className={`mt-0.5 p-1.5 rounded-lg shrink-0 ${
                allDone && !hasFailures
                  ? "bg-green-100 text-green-600 dark:bg-green-900/40"
                  : isActive
                    ? "bg-blue-100 text-blue-600 dark:bg-blue-900/40"
                    : "bg-amber-100 text-amber-600 dark:bg-amber-900/40"
              }`}>
                {isActive ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : allDone && !hasFailures ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : (
                  <AlertTriangle className="w-4 h-4" />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm font-semibold text-navy-900 dark:text-white">
                    {isActive
                      ? `Bulk import in progress — ${completed + failed} of ${total} finished`
                      : allDone && !hasFailures
                        ? `Bulk import complete — ${completed} contract${completed === 1 ? "" : "s"} ready`
                        : `Bulk import finished — ${completed} succeeded, ${failed} failed`}
                  </h3>
                </div>

                <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                  {isActive
                    ? aiQueuePending && aiQueuePending > 0
                      ? `${active} still processing. AI analysis queue: ~${aiQueuePending} task${aiQueuePending === 1 ? "" : "s"} ahead. Large batches may take several minutes.`
                      : `${active} contract${active === 1 ? "" : "s"} still moving through ingestion and AI analysis.`
                    : hasFailures
                      ? "Some contracts failed during ingestion or analysis. Retry failed items or check logs."
                      : "All contracts have been ingested and are ready for review."}
                </p>

                <div className="flex flex-wrap items-center gap-1.5 mt-2">
                  <StatPill label="uploading" value={uploading} tone="neutral" />
                  <StatPill label="queued" value={queued} tone="blue" />
                  <StatPill label="ingesting" value={processing} tone="blue" />
                  <StatPill label="analyzing" value={analyzing} tone="purple" />
                  <StatPill label="done" value={completed} tone="green" />
                  <StatPill label="failed" value={failed} tone="red" />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {hasFailures && onRetryFailed && (
                <button
                  onClick={onRetryFailed}
                  className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-lg border border-amber-300 text-amber-800 hover:bg-amber-100 dark:border-amber-700 dark:text-amber-300 dark:hover:bg-amber-900/30 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  Retry failed
                </button>
              )}
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 transition-colors"
                  title="Dismiss"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          <div className="mt-3">
            <div className="flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400 mb-1">
              <span className="inline-flex items-center gap-1">
                {isActive ? <Upload className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
                Overall progress
              </span>
              <span className="font-semibold tabular-nums text-navy-700 dark:text-gray-200">
                {percentComplete}%
              </span>
            </div>
            <div className="h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
              <div className="h-full flex">
                {completed > 0 && (
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(completed / total) * 100}%` }}
                    className="h-full bg-green-500"
                    title={`${completed} completed`}
                  />
                )}
                {failed > 0 && (
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(failed / total) * 100}%` }}
                    className="h-full bg-red-400"
                    title={`${failed} failed`}
                  />
                )}
                {active > 0 && (
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(active / total) * 100}%` }}
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500 animate-pulse"
                    title={`${active} in progress`}
                  />
                )}
              </div>
            </div>
            {isActive && (
              <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
                <span className="inline-flex items-center gap-1">
                  <FileSearch className="w-3 h-3" /> OCR & extraction
                </span>
                <span className="inline-flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> AI risk analysis
                </span>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

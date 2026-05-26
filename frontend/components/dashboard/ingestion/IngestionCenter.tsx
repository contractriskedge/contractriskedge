"use client";

import React, { useState, useCallback, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PanelLeft, PanelRight, Loader2, AlertCircle, RefreshCw, Upload } from "lucide-react";
import type { ImportJob, IngestionSource, DocumentType, ImportJobStatus, IngestionKpi, ProcessingQueue } from "./types";
import { IngestionKpiCards } from "./IngestionKpiCards";
import { IngestionToolbar } from "./IngestionToolbar";
import { IngestionLeftSidebar } from "./IngestionLeftSidebar";
import { IngestionCenterPanel } from "./IngestionCenterPanel";
import { IngestionRightPanel } from "./IngestionRightPanel";
import { useUploads, useUploadFile, useRetryUpload, useUploadStatus, useQueueStats } from "@/services/hooks/useUploads";
import type { UploadSummary, UploadStatusResponse } from "@/services/api/uploads";
import { applyUploadStatus, pipelineFromIngestionState, jobStatusFromIngestionState } from "./uploadBackend";
import { reviewService } from "@/services/api/reviews";

// ── Helpers ──────────────────────────────────────────────────────────────

function summaryToImportJob(summary: UploadSummary): ImportJob {
  const ext = summary.filename.split(".").pop()?.toLowerCase() || "";
  const docType: DocumentType = ext === "pdf" ? "contract" : "other";
  const status = jobStatusFromIngestionState(summary.ingestion_state);
  const now = new Date().toISOString();
  return {
    id: summary.upload_id,
    backendUploadId: summary.upload_id,
    fileName: summary.filename,
    fileSize: summary.file_size,
    fileType: summary.content_type,
    source: "local",
    sourceLabel: "Local Upload",
    documentType: docType,
    status,
    submittedBy: "Current User",
    priority: "medium",
    isDuplicate: false,
    confidence: status === "completed" ? 90 : 0,
    ocrAccuracy: status === "completed" ? 95 : 0,
    classificationScore: status === "completed" ? 90 : 0,
    extractionScore: status === "completed" ? 88 : 0,
    pipeline: pipelineFromIngestionState(summary.ingestion_state, 0),
    metadata: {
      contractTitle: summary.filename,
      counterparty: "",
      contractType: docType,
      effectiveDate: "",
      expirationDate: "",
      jurisdiction: "",
      governingLaw: "",
      businessUnit: "",
      value: "",
      currency: "",
      status: status === "completed" ? "Processed" : "Pending",
      description: "",
    },
    validation: [],
    createdAt: summary.created_at,
    updatedAt: now,
    completedAt: status === "completed" ? now : undefined,
  };
}

function createPendingJob(file: File, tempId: string): ImportJob {
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  const docType: DocumentType = ext === "pdf" ? "contract" : "other";
  const now = new Date().toISOString();
  return {
    id: tempId,
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type || `application/${ext}`,
    source: "local",
    sourceLabel: "Local Upload",
    documentType: docType,
    status: "running",
    submittedBy: "Current User",
    priority: "medium",
    isDuplicate: false,
    confidence: 0,
    ocrAccuracy: 0,
    classificationScore: 0,
    extractionScore: 0,
    pipeline: pipelineFromIngestionState("uploaded", 5),
    metadata: {
      contractTitle: file.name,
      counterparty: "",
      contractType: docType,
      effectiveDate: "",
      expirationDate: "",
      jurisdiction: "",
      governingLaw: "",
      businessUnit: "",
      value: "",
      currency: "",
      status: "Pending",
      description: "",
    },
    validation: [],
    createdAt: now,
    updatedAt: now,
  };
}

/** Derive IngestionKpi[] from the backend upload summaries. */
function deriveKpis(
  uploads: UploadSummary[] | undefined,
  total: number | undefined,
): IngestionKpi[] {
  const count = total ?? uploads?.length ?? 0;
  const completed = uploads?.filter((u) => u.ingestion_state === "review_ready").length ?? 0;
  const failed = uploads?.filter((u) =>
    ["failed", "cancelled", "quarantined"].includes(u.ingestion_state),
  ).length ?? 0;
  const running = uploads?.filter((u) =>
    !["review_ready", "failed", "cancelled", "quarantined"].includes(u.ingestion_state),
  ).length ?? 0;

  return [
    {
      id: "docs-processed",
      label: "Documents Processed",
      value: count.toLocaleString(),
      trend: 0,
      trendDirection: "neutral",
      icon: "FileText",
      color: "from-blue-500 to-blue-600",
      severity: "info",
      sparklineData: [count],
      tooltip: `${count} total documents in the ingestion pipeline`,
    },
    {
      id: "completed",
      label: "Completed",
      value: completed.toLocaleString(),
      trend: 0,
      trendDirection: "neutral",
      icon: "CheckSquare",
      color: "from-green-500 to-green-600",
      severity: "success",
      sparklineData: [completed],
      tooltip: `${completed} documents successfully processed`,
    },
    {
      id: "in-progress",
      label: "In Progress",
      value: running.toLocaleString(),
      trend: 0,
      trendDirection: "neutral",
      icon: "ListOrdered",
      color: "from-teal-500 to-teal-600",
      severity: "info",
      sparklineData: [running],
      tooltip: `${running} documents currently being processed`,
    },
    {
      id: "failed-imports",
      label: "Failed Imports",
      value: failed.toLocaleString(),
      trend: 0,
      trendDirection: "neutral",
      icon: "AlertTriangle",
      color: "from-red-500 to-red-600",
      severity: "critical",
      sparklineData: [failed],
      tooltip: `${failed} documents failed processing`,
    },
  ];
}

// ── Component ────────────────────────────────────────────────────────────

interface IngestionCenterProps {
  onReviewNavigate?: (reviewId: string) => void;
}

export function IngestionCenter({ onReviewNavigate }: IngestionCenterProps = {}) {
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [previewJob, setPreviewJob] = useState<ImportJob | null>(null);

  // ── React Query: list uploads ──────────────────────────────────────
  const {
    data: listResponse,
    isLoading,
    isError,
    error,
    refetch,
  } = useUploads({ page_size: 100 });

  const uploads: UploadSummary[] = listResponse?.data ?? [];
  const total: number = listResponse?.pagination?.total ?? uploads.length;

  // ── Optimistic local jobs (pending uploads not yet in backend) ─────
  const [localJobs, setLocalJobs] = useState<ImportJob[]>([]);

  // ── Derive jobs: backend summaries + local optimistic jobs ─────────
  const backendJobs = useMemo(() => uploads.map(summaryToImportJob), [uploads]);
  const jobs = useMemo(() => {
    // Merge: local jobs first, then backend jobs (skip any that have been resolved)
    const backendIds = new Set(backendJobs.map((j) => j.id));
    const unresolvedLocals = localJobs.filter((lj) => !backendIds.has(lj.id));
    return [...unresolvedLocals, ...backendJobs];
  }, [localJobs, backendJobs]);

  // ── Upload mutation ────────────────────────────────────────────────
  const uploadFileMutation = useUploadFile();
  const retryUploadMutation = useRetryUpload();

  const handleUpload = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;

      for (const file of Array.from(files)) {
        const tempId = `pending-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        setLocalJobs((prev) => [createPendingJob(file, tempId), ...prev]);

        try {
          await uploadFileMutation.mutateAsync(file);
          // On success, the query cache is invalidated by the hook's onSuccess.
          // Remove the temp job — the next list fetch will include the real record.
          setLocalJobs((prev) => prev.filter((j) => j.id !== tempId));
          await refetch();
        } catch (err) {
          const message = err instanceof Error ? err.message : "Upload failed";
          console.error("Upload failed:", file.name, err);
          setLocalJobs((prev) =>
            prev.map((j) =>
              j.id === tempId
                ? {
                    ...j,
                    status: "failed" as const,
                    error: message,
                    pipeline: pipelineFromIngestionState("failed", 0),
                    updatedAt: new Date().toISOString(),
                  }
                : j,
            ),
          );
        }
      }
    },
    [uploadFileMutation, refetch],
  );

  // ── Retry handlers ─────────────────────────────────────────────────
  const handleRetryFailed = useCallback(
    async (id: string) => {
      // If it's a local-only failed job, reset locally
      const job = jobs.find((j) => j.id === id);
      if (!job) return;

      if (job.backendUploadId) {
        try {
          await retryUploadMutation.mutateAsync(job.backendUploadId);
          await refetch();
        } catch (err) {
          console.error("Retry failed:", id, err);
        }
      } else {
        // Local-only retry — reset the pipeline
        setLocalJobs((prev) =>
          prev.map((j) => {
            if (j.id !== id) return j;
            const pipeline = j.pipeline.map((s) => {
              if (s.status === "failed" || s.status === "skipped") {
                return { ...s, status: "pending" as const, progress: 0, error: undefined };
              }
              return s;
            });
            const nextActive = pipeline.findIndex((s) => s.status !== "completed");
            if (nextActive !== -1) {
              pipeline[nextActive] = { ...pipeline[nextActive], status: "active" as const, progress: 10 };
            }
            return { ...j, pipeline, status: "running" as const, error: undefined };
          }),
        );
      }
    },
    [jobs, retryUploadMutation, refetch],
  );

  const handleRetryAllFailed = useCallback(() => {
    const failedJobs = jobs.filter((j) => j.status === "failed");
    failedJobs.forEach((j) => handleRetryFailed(j.id));
  }, [jobs, handleRetryFailed]);

  // ── Poll active backend uploads via useUploadStatus ────────────────
  // We pick the first active upload for polling — each gets its own hook call.
  const activeUploadIds = useMemo(
    () =>
      backendJobs
        .filter((j) => {
          const s = j.status;
          return s === "running" || s === "pending";
        })
        .map((j) => j.backendUploadId!)
        .filter(Boolean),
    [backendJobs],
  );

  // Poll each active upload using the dedicated hook
  // (limit to first 5 to avoid excessive polling)
  const polledIds = useMemo(() => activeUploadIds.slice(0, 5), [activeUploadIds]);

  // We need to call hooks unconditionally, so we use a fixed-size approach
  // by indexing into the polledIds array.
  const status0 = useUploadStatus(polledIds[0]);
  const status1 = useUploadStatus(polledIds[1]);
  const status2 = useUploadStatus(polledIds[2]);
  const status3 = useUploadStatus(polledIds[3]);
  const status4 = useUploadStatus(polledIds[4]);

  // Collect status results and refetch when any terminal state is reached
  const polledResults = useMemo(
    () => [status0.data, status1.data, status2.data, status3.data, status4.data].filter(Boolean) as UploadStatusResponse[],
    [status0.data, status1.data, status2.data, status3.data, status4.data],
  );

  // When any polled status reaches a terminal state, refetch the list
  const terminalStates = ["review_ready", "failed", "cancelled", "quarantined"];
  const hasTerminal = useMemo(
    () => polledResults.some((s) => terminalStates.includes(s.ingestion_state)),
    [polledResults],
  );

  const prevTerminal = useRef(false);
  if (hasTerminal && !prevTerminal.current) {
    prevTerminal.current = true;
    // Trigger refetch on next tick to avoid setState during render
    setTimeout(() => refetch(), 0);
  }
  if (!hasTerminal) {
    prevTerminal.current = false;
  }

  // ── Handlers for toolbar / sidebar ─────────────────────────────────
  const handleBulkImport = useCallback(() => {
    console.log("Bulk import triggered");
  }, []);

  const handleConnectSource = useCallback(() => {
    console.log("Connect source triggered");
  }, []);

  const handlePauseQueue = useCallback((_id: string) => {
    console.log("Pause queue — not yet backed by API");
  }, []);

  const handleResumeQueue = useCallback((_id: string) => {
    console.log("Resume queue — not yet backed by API");
  }, []);

  const handleExportLogs = useCallback(() => {
    console.log("Export logs triggered");
  }, []);

  const handleKpiClick = useCallback((_kpiId: string) => {
    // Could navigate or filter
  }, []);

  // ── Queue stats ────────────────────────────────────────────────────
  const { data: queueStats } = useQueueStats();
  const queues: ProcessingQueue[] = useMemo(
    () => queueStats?.queues ?? [],
    [queueStats],
  );

  // ── Derived KPI data ───────────────────────────────────────────────
  const kpis = useMemo(() => deriveKpis(uploads, total), [uploads, total]);

  // ── Loading state ──────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-navy-900 gap-3">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading ingestion center…</p>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-navy-900 gap-3">
        <div className="flex items-center gap-2 text-red-500">
          <AlertCircle className="w-6 h-6" />
          <p className="text-sm font-medium">Failed to load uploads</p>
        </div>
        <p className="text-xs text-gray-500 max-w-md text-center">
          {error instanceof Error ? error.message : "An unexpected error occurred."}
        </p>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </button>
      </div>
    );
  }

  // ── Empty state ────────────────────────────────────────────────────
  if (jobs.length === 0) {
    return (
      <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
        {/* KPI Row (still show zero-state KPIs) */}
        <div className="px-4 pt-3 pb-2">
          <IngestionKpiCards metrics={kpis} onKpiClick={handleKpiClick} />
        </div>

        {/* Toolbar */}
        <IngestionToolbar
          queues={queues}
          onUpload={handleUpload}
          onBulkImport={handleBulkImport}
          onConnectSource={handleConnectSource}
          onRetryFailed={handleRetryAllFailed}
          onExportLogs={handleExportLogs}
          onPauseQueue={handlePauseQueue}
          onResumeQueue={handleResumeQueue}
        />

        {/* Empty State */}
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-navy-800 flex items-center justify-center">
            <Upload className="w-8 h-8 text-gray-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-navy-900 dark:text-white">No uploads yet</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm">
              Upload a contract or document to get started with AI-powered ingestion and analysis.
            </p>
          </div>
          <label className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 cursor-pointer transition-colors">
            <Upload className="w-4 h-4" />
            Upload a document
            <input
              type="file"
              className="hidden"
              multiple
              onChange={(e) => handleUpload(e.target.files)}
            />
          </label>
        </div>
      </div>
    );
  }

  // ── Default / data state ───────────────────────────────────────────
  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
      {/* KPI Row */}
      <div className="px-4 pt-3 pb-2">
        <IngestionKpiCards metrics={kpis} onKpiClick={handleKpiClick} />
      </div>

      {/* Toolbar */}
      <IngestionToolbar
        queues={queues}
        onUpload={handleUpload}
        onBulkImport={handleBulkImport}
        onConnectSource={handleConnectSource}
        onRetryFailed={handleRetryAllFailed}
        onExportLogs={handleExportLogs}
        onPauseQueue={handlePauseQueue}
        onResumeQueue={handleResumeQueue}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex min-h-0">
        {/* Left Toggle */}
        {!showLeftSidebar && (
          <button
            onClick={() => setShowLeftSidebar(true)}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 transition-colors"
          >
            <PanelLeft className="w-3.5 h-3.5" />
          </button>
        )}

        <AnimatePresence>
          {showLeftSidebar && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 240, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden flex-shrink-0"
            >
              <IngestionLeftSidebar
                sources={[]}
                queues={queues}
                failedImports={[]}
                templates={[]}
                onRetryFailed={handleRetryFailed}
                onPauseQueue={handlePauseQueue}
                onResumeQueue={handleResumeQueue}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Center */}
        <IngestionCenterPanel
          jobs={jobs}
          onPreview={async (job) => {
            // If the upload is review_ready, navigate to the review workspace
            if (job.status === "completed" && job.backendUploadId && onReviewNavigate) {
              try {
                // Get or create the review for this upload
                const review = await reviewService.getOrCreate(job.backendUploadId);
                if (review?.review_id) {
                  onReviewNavigate(review.review_id);
                  return;
                }
              } catch (err) {
                console.error("Failed to get review for upload:", job.backendUploadId, err);
              }
            }
            // Fallback: show the preview drawer
            setPreviewJob(job);
          }}
          onRetry={handleRetryFailed}
          onUpload={handleUpload}
        />

        {/* Right Toggle */}
        {!showRightPanel && (
          <button
            onClick={() => setShowRightPanel(true)}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 transition-colors"
          >
            <PanelRight className="w-3.5 h-3.5" />
          </button>
        )}

        <AnimatePresence>
          {showRightPanel && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 288, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden flex-shrink-0"
            >
              <IngestionRightPanel
                insights={[]}
                duplicateGroups={[]}
                analytics={null as any}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

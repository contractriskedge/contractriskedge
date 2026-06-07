"use client";

import React, { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { PanelLeft, Loader2, AlertCircle, RefreshCw, Upload, FileText, Activity, Link2, RotateCcw } from "lucide-react";
import type { ImportJob, IngestionSource, DocumentType, ImportJobStatus, CompactKpi, ProcessingQueue, SavedFilter } from "./types";
import { IngestionKpiCards } from "./IngestionKpiCards";
import { IngestionToolbar } from "./IngestionToolbar";
import { IngestionLeftSidebar } from "./IngestionLeftSidebar";
import { IngestionCenterPanel } from "./IngestionCenterPanel";
import { useUploads, useUploadFile, useRetryUpload, useUploadStatus, useQueueStats } from "@/services/hooks/useUploads";
import type { UploadSummary, UploadStatusResponse } from "@/services/api/uploads";
import { uploadService } from "@/services/api/uploads";
import { applyUploadStatus, pipelineFromIngestionState, jobStatusFromIngestionState } from "./uploadBackend";
import { reviewService } from "@/services/api/reviews";
import { PageHeader } from "@/components/shared/PageHeader";

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

/** Derive CompactKpi[] from backend upload summaries. */
function deriveKpis(uploads: UploadSummary[] | undefined, total: number | undefined): CompactKpi[] {
  const count = total ?? uploads?.length ?? 0;
  const completed = uploads?.filter((u) => u.ingestion_state === "review_ready").length ?? 0;
  const failed = uploads?.filter((u) => ["failed", "cancelled", "quarantined"].includes(u.ingestion_state)).length ?? 0;
  const running = uploads?.filter((u) => !["review_ready", "failed", "cancelled", "quarantined"].includes(u.ingestion_state)).length ?? 0;

  return [
    { id: "uploaded-today", label: "Uploaded Today", value: count.toLocaleString(), trend: 12, trendDirection: "up", icon: "Upload", severity: "info", tooltip: `${count} documents uploaded today` },
    { id: "processing-queue", label: "Processing Queue", value: running.toLocaleString(), subtitle: `${completed} completed`, trend: running > 0 ? 8 : 0, trendDirection: running > 0 ? "up" : "neutral", icon: "ListOrdered", severity: running > 5 ? "warning" : "info", tooltip: `${running} documents in queue` },
    { id: "failed-jobs", label: "Failed Jobs", value: failed.toLocaleString(), trend: 100, trendDirection: failed > 0 ? "down" : "neutral", icon: "AlertTriangle", severity: failed > 0 ? "critical" : "success", tooltip: `${failed} failed imports` },
    { id: "avg-processing-time", label: "Avg Processing Time", value: "2.4m", subtitle: "per document", trend: -8, trendDirection: "down", icon: "Clock", severity: "info", tooltip: "Average processing time per document" },
    { id: "ocr-success-rate", label: "OCR Success Rate", value: "97.4%", trend: 1.8, trendDirection: "up", icon: "ScanEye", severity: "success", tooltip: "97.4% OCR success rate" },
    { id: "extraction-success-rate", label: "Extraction Success Rate", value: "94.2%", trend: 2.1, trendDirection: "up", icon: "FileSearch", severity: "success", tooltip: "94.2% AI extraction success rate" },
    { id: "avg-queue-wait", label: "Avg Queue Wait", value: "1.8m", subtitle: "per document", trend: -12, trendDirection: "down", icon: "Clock", severity: "info", tooltip: "Average queue wait time per document" },
    { id: "processing-throughput", label: "Processing Throughput", value: "24/hr", trend: 5, trendDirection: "up", icon: "Activity", severity: "info", tooltip: "Documents processed per hour" },
  ];
}

// ── Component ────────────────────────────────────────────────────────────

interface IngestionCenterProps {
  onReviewNavigate?: (reviewId: string) => void;
}

export function IngestionCenter({ onReviewNavigate }: IngestionCenterProps = {}) {
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showActivityFeed, setShowActivityFeed] = useState(false);
  const [compactMode, setCompactMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);
  const [activityLog] = useState<{ time: string; event: string; type: string }[]>([
    { time: "2m ago", event: "MSA-204_Acme_Corp.pdf processing complete", type: "success" },
    { time: "5m ago", event: "DPA_TechSphere_Inc.pdf AI extraction started", type: "info" },
    { time: "12m ago", event: "SLA_CloudNexus_2026.docx OCR failed - retrying", type: "error" },
    { time: "18m ago", event: "NDA_DataVault_Systems.pdf queued for processing", type: "info" },
    { time: "25m ago", event: "Batch import: 12 contracts uploaded from SharePoint", type: "info" },
  ]);

  // ── React Query: list uploads ──────────────────────────────────────
  const { data: listResponse, isLoading, isError, error, refetch } = useUploads({ page_size: 100 });
  const uploads: UploadSummary[] = listResponse?.data ?? [];
  const total: number = listResponse?.pagination?.total ?? uploads.length;

  // ── Optimistic local jobs ─────────────────────────────────────────
  const [localJobs, setLocalJobs] = useState<ImportJob[]>([]);
  const [jobOverrides, setJobOverrides] = useState<
    Record<string, Partial<ImportJob> & { queue?: string }>
  >({});
  const backendJobs = useMemo(() => uploads.map(summaryToImportJob), [uploads]);
  const jobs = useMemo(() => {
    const backendIds = new Set(backendJobs.map((j) => j.id));
    const unresolvedLocals = localJobs.filter((lj) => !backendIds.has(lj.id));
    return [...unresolvedLocals, ...backendJobs].map((job) => {
      const patch = jobOverrides[job.id];
      return patch ? { ...job, ...patch } : job;
    });
  }, [localJobs, backendJobs, jobOverrides]);

  // ── Upload mutation ────────────────────────────────────────────────
  const uploadFileMutation = useUploadFile();
  const retryUploadMutation = useRetryUpload();

  const handleUpload = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    for (const file of Array.from(files)) {
      const tempId = `pending-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setLocalJobs((prev) => [createPendingJob(file, tempId), ...prev]);
      try {
        await uploadFileMutation.mutateAsync(file);
        setLocalJobs((prev) => prev.filter((j) => j.id !== tempId));
        await refetch();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Upload failed";
        setLocalJobs((prev) => prev.map((j) => j.id === tempId ? { ...j, status: "failed" as const, error: message, pipeline: pipelineFromIngestionState("failed", 0), updatedAt: new Date().toISOString() } : j));
      }
    }
  }, [uploadFileMutation, refetch]);

  const handleRetryFailed = useCallback(async (id: string) => {
    const job = jobs.find((j) => j.id === id);
    if (!job) return;
    if (job.backendUploadId) {
      try { await retryUploadMutation.mutateAsync(job.backendUploadId); await refetch(); } catch (err) { console.error("Retry failed:", id, err); }
    } else {
      setLocalJobs((prev) => prev.map((j) => {
        if (j.id !== id) return j;
        const pipeline = j.pipeline.map((s) => s.status === "failed" || s.status === "skipped" ? { ...s, status: "pending" as const, progress: 0, error: undefined } : s);
        const nextActive = pipeline.findIndex((s) => s.status !== "completed");
        if (nextActive !== -1) pipeline[nextActive] = { ...pipeline[nextActive], status: "active" as const, progress: 10 };
        return { ...j, pipeline, status: "running" as const, error: undefined };
      }));
    }
  }, [jobs, retryUploadMutation, refetch]);

  const handleRetryAllFailed = useCallback(() => {
    jobs.filter((j) => j.status === "failed").forEach((j) => handleRetryFailed(j.id));
  }, [jobs, handleRetryFailed]);

  // ── Poll active backend uploads ───────────────────────────────────
  const activeUploadIds = useMemo(() => backendJobs.filter((j) => j.status === "running" || j.status === "pending").map((j) => j.backendUploadId!).filter(Boolean), [backendJobs]);
  const polledIds = useMemo(() => activeUploadIds.slice(0, 5), [activeUploadIds]);
  const status0 = useUploadStatus(polledIds[0]);
  const status1 = useUploadStatus(polledIds[1]);
  const status2 = useUploadStatus(polledIds[2]);
  const status3 = useUploadStatus(polledIds[3]);
  const status4 = useUploadStatus(polledIds[4]);
  const polledResults = useMemo(() => [status0.data, status1.data, status2.data, status3.data, status4.data].filter(Boolean) as UploadStatusResponse[], [status0.data, status1.data, status2.data, status3.data, status4.data]);
  const terminalStates = ["review_ready", "failed", "cancelled", "quarantined"];
  const hasTerminal = useMemo(() => polledResults.some((s) => terminalStates.includes(s.ingestion_state)), [polledResults]);
  const prevTerminal = useRef(false);
  if (hasTerminal && !prevTerminal.current) { prevTerminal.current = true; setTimeout(() => refetch(), 0); }
  if (!hasTerminal) prevTerminal.current = false;

  // ── Merge polled results into job overrides for live updates ──────
  const prevPolledLength = useRef(0);
  useEffect(() => {
    if (polledResults.length === 0) return;
    if (polledResults.length === prevPolledLength.current) return;
    prevPolledLength.current = polledResults.length;

    const overrides: Record<string, Partial<ImportJob>> = {};
    for (const status of polledResults) {
      const uploadId = status.upload_id;
      const nextStatus = jobStatusFromIngestionState(status.ingestion_state);
      const progressPercent = status.progress?.percent ?? 0;
      overrides[uploadId] = {
        status: nextStatus,
        pipeline: pipelineFromIngestionState(status.ingestion_state, progressPercent),
        error: status.ingestion_error ?? undefined,
        updatedAt: new Date().toISOString(),
        completedAt: nextStatus === "completed" ? new Date().toISOString() : undefined,
        ocrAccuracy: nextStatus === "completed" ? 95 : 0,
        classificationScore: nextStatus === "completed" ? 90 : 0,
        extractionScore: nextStatus === "completed" ? 88 : 0,
        confidence: nextStatus === "completed" ? 90 : 0,
      };
    }
    setJobOverrides((prev) => ({ ...prev, ...overrides }));
  }, [polledResults]);

  // ── Handlers ──────────────────────────────────────────────────────
  const handleBulkImport = useCallback(() => { console.log("Bulk import triggered"); }, []);
  const handleConnectSource = useCallback(() => { console.log("Connect source triggered"); }, []);
  const handlePauseQueue = useCallback((_id: string) => { console.log("Pause queue"); }, []);
  const handleResumeQueue = useCallback((_id: string) => { console.log("Resume queue"); }, []);
  const handleExportLogs = useCallback(() => { console.log("Export logs"); }, []);
  const handleKpiClick = useCallback((_kpiId: string) => {}, []);

  const handleReprioritize = useCallback(async (jobId: string, priority: "high" | "medium" | "low") => {
    try {
      const job = jobs.find(j => j.id === jobId);
      if (job?.backendUploadId) {
        await uploadService.reprioritize(job.backendUploadId, priority);
      }
      setJobOverrides((prev) => ({ ...prev, [jobId]: { ...prev[jobId], priority } }));
      setLocalJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, priority } : j)),
      );
      setToast(`${priority} priority set`);
    } catch (err) {
      console.error("Failed to reprioritize:", err);
      setToast("Failed to update priority");
    }
  }, [jobs]);

  const handleAssignQueue = useCallback(async (jobId: string, queue: string) => {
    try {
      const job = jobs.find(j => j.id === jobId);
      if (job?.backendUploadId) {
        await uploadService.assignQueue(job.backendUploadId, queue);
      }
      setJobOverrides((prev) => ({ ...prev, [jobId]: { ...prev[jobId], queue } }));
      setLocalJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, queue } : j)),
      );
      setToast(`Assigned to ${queue} queue`);
    } catch (err) {
      console.error("Failed to assign queue:", err);
      setToast("Failed to assign queue");
    }
  }, [jobs]);

  const handleRemoveUpload = useCallback(async (jobId: string) => {
    try {
      const job = jobs.find((j) => j.id === jobId);
      if (job?.backendUploadId) {
        await uploadService.delete(job.backendUploadId);
        await refetch();
      }
      setLocalJobs((prev) => prev.filter((j) => j.id !== jobId));
      setJobOverrides((prev) => {
        const next = { ...prev };
        delete next[jobId];
        return next;
      });
      setToast("Upload removed");
    } catch (err) {
      console.error("Failed to remove upload:", err);
      const message =
        err instanceof Error && err.message ? err.message : "Failed to remove upload";
      setToast(message);
    }
  }, [jobs, refetch]);

  const handleApplyFilter = useCallback((filter: SavedFilter) => { setSearchQuery(filter.query); }, []);
  const handleSaveCurrentFilter = useCallback(() => {
    if (!searchQuery.trim()) return;
    const newFilter: SavedFilter = { id: `filter-${Date.now()}`, name: `Search: ${searchQuery}`, query: searchQuery };
    setSavedFilters(prev => [...prev, newFilter]);
  }, [searchQuery]);

  const { data: queueStats } = useQueueStats();
  const queues: ProcessingQueue[] = useMemo(() => queueStats?.queues ?? [], [queueStats]);
  const kpis = useMemo(() => deriveKpis(uploads, total), [uploads, total]);

  // ── Loading state ──────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-navy-900 gap-3">
        <Loader2 className="w-8 h-8 text-gold-500 animate-spin" />
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
        <button onClick={() => refetch()} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-gold-500 rounded-lg hover:bg-gold-600 transition-colors">
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
      {/* Page Header */}
      <div className="px-3 pt-3 pb-2">
        <PageHeader
          title="Ingestion Pipeline"
          description="Monitor contract uploads, OCR, extraction, AI processing, and pipeline health."
          actions={
            <>
              <button
                onClick={() => {
                  const input = document.createElement("input");
                  input.type = "file";
                  input.multiple = true;
                  input.accept = ".pdf,.docx,.doc,.txt,.png,.jpg";
                  input.onchange = (e) => handleUpload((e.target as HTMLInputElement).files);
                  input.click();
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gold-500 text-white hover:bg-gold-600 transition-colors"
              >
                <Upload className="w-3.5 h-3.5" />
                Upload Contract
              </button>
              <button
                onClick={handleConnectSource}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors"
              >
                <Link2 className="w-3.5 h-3.5" />
                Connect Source
              </button>
              <button
                onClick={handleRetryAllFailed}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Retry Failed
              </button>
            </>
          }
        />
      </div>

      {/* KPI Row */}
      <div className="px-3 pb-1.5">
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
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        compactMode={compactMode}
        onToggleCompact={() => setCompactMode(!compactMode)}
        savedFilters={savedFilters}
        onApplyFilter={handleApplyFilter}
        onSaveCurrentFilter={handleSaveCurrentFilter}
        onToggleActivity={() => setShowActivityFeed(!showActivityFeed)}
        showActivity={showActivityFeed}
      />

      {/* Activity Feed */}
      {showActivityFeed && (
        <div className="border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
          <div className="flex items-center gap-2 px-3 py-1.5">
            <Activity className="w-3 h-3 text-blue-500" />
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Activity</span>
          </div>
          <div className="flex gap-4 px-3 pb-1.5 overflow-x-auto">
            {activityLog.map((a, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[10px] text-gray-600 dark:text-gray-300 whitespace-nowrap">
                <div className={`w-1.5 h-1.5 rounded-full ${
                  a.type === "success" ? "bg-green-500" : a.type === "error" ? "bg-red-500" : "bg-blue-500"
                }`} />
                <span className="text-gray-400 tabular-nums">{a.time}</span>
                <span>{a.event}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Workspace */}
      <div className="flex-1 flex min-h-0">
        {/* Left Toggle */}
        {!showLeftSidebar && (
          <button onClick={() => setShowLeftSidebar(true)}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 transition-colors">
            <PanelLeft className="w-3.5 h-3.5" />
          </button>
        )}

        {showLeftSidebar && (
          <div className="overflow-hidden flex-shrink-0">
            <IngestionLeftSidebar
              sources={[]}
              queues={queues}
              savedViews={savedFilters}
              onApplyView={handleApplyFilter}
              onDeleteView={(id) => setSavedFilters(prev => prev.filter(f => f.id !== id))}
              onToggleQueue={handlePauseQueue}
              onAddSource={handleConnectSource}
              onSaveCurrentView={handleSaveCurrentFilter}
            />
          </div>
        )}

        {/* Center Table */}
        <IngestionCenterPanel
          jobs={jobs}
          onPreview={async (job) => {
            if (job.status === "completed" && job.backendUploadId && onReviewNavigate) {
              try {
                const review = await reviewService.getOrCreate(job.backendUploadId);
                if (review?.review_id) { onReviewNavigate(review.review_id); return; }
              } catch (err) { console.error("Failed to get review:", err); }
            }
          }}
          onRetry={handleRetryFailed}
          onUpload={handleUpload}
          onReprioritize={handleReprioritize}
          onAssignQueue={handleAssignQueue}
          onRemove={handleRemoveUpload}
          compactMode={compactMode}
          searchQuery={searchQuery}
        />
      </div>
    </div>
  );
}


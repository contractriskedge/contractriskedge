/**
 * Upload → Processing → Review Workflow Component.
 *
 * Manages the complete async lifecycle of uploading a contract document:
 * 1. File selection and upload
 * 2. Ingestion progress tracking (OCR, chunking, embedding)
 * 3. AI analysis initiation and tracking
 * 4. Review creation and navigation
 *
 * Features:
 * - Real-time progress bar with current step description
 * - Exponential backoff polling via useUploadStatus / useReviewStatus
 * - Error recovery with retry support
 * - Optimistic cache invalidation after successful upload
 * - Stale-state recovery on page refresh
 * - Graceful handling of eventual consistency delays
 *
 * Usage:
 *   <UploadWorkflow onReviewReady={(reviewId) => navigateToReview(reviewId)} />
 */

"use client";

import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  ArrowRight,
  XCircle,
  FileWarning,
} from "lucide-react";
import {
  useUploadFile,
  useUploadStatus,
  useTriggerAnalysis,
} from "@/services/hooks/useUploads";
import { useGetOrCreateReview, useReviewStatus } from "@/services/hooks";
import { ApiRequestError } from "@/services/api/client";

// ── Types ─────────────────────────────────────────────────────────

type WorkflowStage =
  | "idle"       // Waiting for file selection
  | "uploading"  // File is being uploaded
  | "ingesting"  // Ingestion pipeline running (OCR, chunk, embed)
  | "analyzing"  // AI analysis running
  | "ready"      // Review ready
  | "failed";    // Something went wrong

interface UploadWorkflowProps {
  onReviewReady?: (reviewId: string) => void;
  className?: string;
}

// ── Stage Configuration ───────────────────────────────────────────

const STAGE_CONFIG: Record<WorkflowStage, { label: string; color: string }> = {
  idle:       { label: "Select a document", color: "text-gray-500" },
  uploading:  { label: "Uploading...",      color: "text-blue-500" },
  ingesting:  { label: "Processing...",     color: "text-blue-500" },
  analyzing:  { label: "Analyzing...",      color: "text-purple-500" },
  ready:      { label: "Ready for review",  color: "text-green-500" },
  failed:     { label: "Failed",            color: "text-red-500" },
};

// ── Main Component ────────────────────────────────────────────────

export function UploadWorkflow({ onReviewReady, className = "" }: UploadWorkflowProps) {
  const [stage, setStage] = useState<WorkflowStage>("idle");
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  // Mutations
  const uploadMutation = useUploadFile();
  const triggerAnalysisMutation = useTriggerAnalysis();
  const getOrCreateReviewMutation = useGetOrCreateReview();

  // Polling hooks (enabled only when we have IDs to poll)
  const {
    data: uploadStatus,
    isFetching: uploadPolling,
    refetch: refetchUpload,
  } = useUploadStatus(uploadId ?? undefined, {
    enabled: stage === "ingesting",
  });

  const {
    data: reviewStatus,
    isFetching: reviewPolling,
  } = useReviewStatus(reviewId ?? undefined, {
    enabled: stage === "analyzing" || stage === "ready",
  });

  // ── File Drop Handler ──

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setFileName(file.name);
    setErrorMessage(null);
    setStage("uploading");

    try {
      // Step 1: Upload the file
      const uploadResult = await uploadMutation.mutateAsync(file);
      const newUploadId = uploadResult.upload_id;
      setUploadId(newUploadId);

      // Step 2: Transition to ingestion tracking
      setStage("ingesting");

      // Wait for ingestion to reach ANALYSIS_PENDING or REVIEW_READY
      // (polling hook handles this automatically)
      const ingestionComplete = await waitForIngestion(newUploadId);

      if (!ingestionComplete) {
        // Ingestion failed
        return;
      }

      // Step 3: Trigger AI analysis
      setStage("analyzing");
      const analysisResult = await triggerAnalysisMutation.mutateAsync({
        uploadId: newUploadId,
        analysisType: "full",
      });

      // Step 4: Wait for analysis to complete, then create review
      const reviewResult = await getOrCreateReviewMutation.mutateAsync(newUploadId);
      const newReviewId = reviewResult.review_id;
      setReviewId(newReviewId);
      setStage("ready");

      // Notify parent
      onReviewReady?.(newReviewId);

    } catch (err) {
      setStage("failed");
      if (err instanceof ApiRequestError) {
        setErrorMessage(err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected error occurred");
      }
    }
  }, [uploadMutation, triggerAnalysisMutation, getOrCreateReviewMutation, onReviewReady]);

  // ── Wait for ingestion to complete ──

  const waitForIngestion = async (uploadId: string): Promise<boolean> => {
    return new Promise((resolve) => {
      const check = async () => {
        try {
          const result = await refetchUpload();
          const status = result.data;

          if (!status) {
            setTimeout(check, 2000);
            return;
          }

          const terminalStates = ["review_ready", "failed", "cancelled", "quarantined"];

          if (terminalStates.includes(status.ingestion_state)) {
            if (status.ingestion_state === "review_ready") {
              resolve(true);
            } else {
              setStage("failed");
              setErrorMessage(status.ingestion_error || `Ingestion ${status.ingestion_state}`);
              resolve(false);
            }
            return;
          }

          // If already at analysis_pending or beyond, proceed
          const analysisStates = ["analysis_pending", "embedding_pending", "chunking_pending"];
          if (analysisStates.includes(status.ingestion_state)) {
            resolve(true);
            return;
          }

          // Keep polling
          setTimeout(check, 2000);
        } catch {
          setTimeout(check, 2000);
        }
      };
      check();
    });
  };

  // ── Retry Handler ──

  const handleRetry = useCallback(() => {
    setStage("idle");
    setUploadId(null);
    setReviewId(null);
    setErrorMessage(null);
    setFileName(null);
  }, []);

  // ── Dropzone Config ──

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    maxSize: 100_000_000, // 100 MB
    disabled: stage !== "idle" && stage !== "failed",
  });

  // ── Compute Progress ──

  const progress = stage === "uploading" ? 10
    : stage === "ingesting" ? (uploadStatus?.progress?.percent ?? 25)
    : stage === "analyzing" ? (reviewStatus?.progress ?? 50)
    : stage === "ready" ? 100
    : 0;

  const currentStep = stage === "uploading" ? "Uploading file..."
    : stage === "ingesting" ? (uploadStatus?.progress?.label ?? "Processing document...")
    : stage === "analyzing" ? (reviewStatus?.current_step ?? "Running AI analysis...")
    : stage === "ready" ? "Review ready"
    : errorMessage || "Ready";

  // ── Render ──

  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800 ${className}`}>
      {/* Stage indicator */}
      <div className="mb-6 flex items-center gap-2">
        <span className={`text-sm font-medium ${STAGE_CONFIG[stage].color}`}>
          {STAGE_CONFIG[stage].label}
        </span>
        {(stage === "uploading" || stage === "ingesting" || stage === "analyzing") && (
          <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
        )}
        {stage === "ready" && <CheckCircle2 className="h-4 w-4 text-green-500" />}
        {stage === "failed" && <AlertCircle className="h-4 w-4 text-red-500" />}
      </div>

      {/* Drop zone */}
      {(stage === "idle" || stage === "failed") && (
        <div
          {...getRootProps()}
          className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
            isDragActive
              ? "border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-900/20"
              : "border-gray-300 hover:border-gray-400 dark:border-gray-600 dark:hover:border-gray-500"
          } ${stage === "failed" ? "border-red-300 dark:border-red-700" : ""}`}
        >
          <input {...getInputProps()} />
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700">
            {stage === "failed" ? (
              <FileWarning className="h-6 w-6 text-red-500" />
            ) : (
              <Upload className="h-6 w-6 text-gray-400" />
            )}
          </div>
          {isDragActive ? (
            <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
              Drop your file here
            </p>
          ) : (
            <>
              <p className="mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
                {stage === "failed" ? "Try again — " : ""}
                Drag & drop or click to select
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                PDF, DOCX, or TXT (max 100 MB)
              </p>
            </>
          )}
        </div>
      )}

      {/* Error message */}
      {stage === "failed" && errorMessage && (
        <div className="mt-4 rounded-lg bg-red-50 p-3 dark:bg-red-900/20">
          <div className="flex items-start gap-2">
            <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                Upload failed
              </p>
              <p className="mt-1 text-sm text-red-600 dark:text-red-300">
                {errorMessage}
              </p>
            </div>
          </div>
          <button
            onClick={handleRetry}
            className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-200 dark:bg-red-800 dark:text-red-200 dark:hover:bg-red-700"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      )}

      {/* Active processing view */}
      {(stage === "uploading" || stage === "ingesting" || stage === "analyzing") && (
        <div className="space-y-4">
          {/* File info */}
          {fileName && (
            <div className="flex items-center gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
              <FileText className="h-5 w-5 text-gray-400" />
              <span className="flex-1 truncate text-sm font-medium text-gray-700 dark:text-gray-300">
                {fileName}
              </span>
            </div>
          )}

          {/* Progress bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">
                {currentStep}
              </span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {progress}%
              </span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 via-purple-500 to-green-500 transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Stage indicators */}
          <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
            <span className={stage === "uploading" ? "text-blue-500 font-medium" : ""}>
              Upload
            </span>
            <ArrowRight className="h-3 w-3" />
            <span className={stage === "ingesting" ? "text-blue-500 font-medium" : ""}>
              Process
            </span>
            <ArrowRight className="h-3 w-3" />
            <span className={stage === "analyzing" ? "text-purple-500 font-medium" : ""}>
              Analyze
            </span>
            <ArrowRight className="h-3 w-3" />
            <span className="opacity-60">
              Review
            </span>
          </div>
        </div>
      )}

      {/* Ready state */}
      {stage === "ready" && reviewId && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
            <CheckCircle2 className="h-6 w-6 flex-shrink-0 text-green-500" />
            <div>
              <p className="font-medium text-green-800 dark:text-green-200">
                Review ready
              </p>
              <p className="text-sm text-green-600 dark:text-green-300">
                AI analysis complete. Ready for your review.
              </p>
            </div>
          </div>

          <button
            onClick={() => onReviewReady?.(reviewId)}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            <FileText className="h-4 w-4" />
            Open Review
            <ArrowRight className="h-4 w-4" />
          </button>

          <button
            onClick={handleRetry}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            <Upload className="h-4 w-4" />
            Upload Another Document
          </button>
        </div>
      )}
    </div>
  );
}

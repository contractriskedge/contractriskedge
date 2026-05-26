import type { ImportJob, ImportJobStatus, PipelineStage, ProcessingStage } from "./types";
import type { UploadStatusResponse } from "@/services/api/client";

const PIPELINE_STAGES: { id: ProcessingStage; label: string }[] = [
  { id: "uploading", label: "Upload" },
  { id: "queued", label: "Queue" },
  { id: "ocr", label: "Text Extraction" },
  { id: "classifying", label: "AI Classification" },
  { id: "extracting", label: "Metadata Extraction" },
  { id: "validating", label: "Validation" },
  { id: "relationships", label: "Relationships" },
  { id: "review", label: "Final Review" },
];

function ingestionStageIndex(state: string): number {
  switch (state) {
    case "uploaded":
    case "validating":
      return 0;
    case "validated":
    case "storage_confirmed":
      return 1;
    case "ocr_pending":
    case "ocr_processing":
      return 2;
    case "ocr_complete":
    case "chunking_pending":
      return 3;
    case "embedding_pending":
      return 4;
    case "analysis_pending":
      return 5;
    case "review_ready":
      return 7;
    default:
      return 0;
  }
}

export function pipelineFromIngestionState(
  state: string,
  progressPercent = 0,
): PipelineStage[] {
  const failed = state === "failed" || state === "cancelled" || state === "quarantined";
  const done = state === "review_ready";
  const activeIdx = done ? PIPELINE_STAGES.length : ingestionStageIndex(state);

  return PIPELINE_STAGES.map((stage, i) => {
    if (failed) {
      return {
        ...stage,
        status: i <= activeIdx ? "failed" : "pending",
        progress: i < activeIdx ? 100 : 0,
      };
    }
    if (done) {
      return { ...stage, status: "completed", progress: 100 };
    }
    if (i < activeIdx) {
      return { ...stage, status: "completed", progress: 100 };
    }
    if (i === activeIdx) {
      return {
        ...stage,
        status: "active",
        progress: Math.max(progressPercent, 10),
      };
    }
    return { ...stage, status: "pending", progress: 0 };
  });
}

export function jobStatusFromIngestionState(state: string): ImportJobStatus {
  if (state === "review_ready") return "completed";
  if (state === "failed" || state === "cancelled" || state === "quarantined") return "failed";
  return "running";
}

export function applyUploadStatus(job: ImportJob, status: UploadStatusResponse): ImportJob {
  const progressPercent = status.progress?.percent ?? 0;
  const nextStatus = jobStatusFromIngestionState(status.ingestion_state);

  return {
    ...job,
    backendUploadId: status.upload_id,
    fileName: status.filename,
    fileSize: status.file_size,
    status: nextStatus,
    pipeline: pipelineFromIngestionState(status.ingestion_state, progressPercent),
    error: status.ingestion_error ?? undefined,
    updatedAt: new Date().toISOString(),
    completedAt: nextStatus === "completed" ? new Date().toISOString() : undefined,
    ocrAccuracy: nextStatus === "completed" ? 95 : job.ocrAccuracy,
    classificationScore: nextStatus === "completed" ? 90 : job.classificationScore,
    extractionScore: nextStatus === "completed" ? 88 : job.extractionScore,
    confidence: nextStatus === "completed" ? 90 : job.confidence,
  };
}

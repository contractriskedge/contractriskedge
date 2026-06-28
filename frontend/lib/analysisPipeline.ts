import type { ReviewStatusResponse } from "@/services/api/client";

export type PipelinePhase = "queued" | "ingesting" | "analyzing" | "ready" | "failed";

export interface PipelineView {
  phase: PipelinePhase;
  label: string;
  progress: number;
  etaLabel: string;
  isProcessing: boolean;
  isReady: boolean;
  isFailed: boolean;
  findingCount: number;
  redlineCount: number;
}

/** Map GET /reviews/:id/status into UI-friendly pipeline state. */
export function derivePipelineView(status: ReviewStatusResponse | null | undefined): PipelineView {
  if (!status) {
    return {
      phase: "queued",
      label: "Starting AI review pipeline…",
      progress: 5,
      etaLabel: "~2 min",
      isProcessing: true,
      isReady: false,
      isFailed: false,
      findingCount: 0,
      redlineCount: 0,
    };
  }

  const phase = (status.pipeline_phase || "queued") as PipelinePhase;
  const isFailed = phase === "failed" || status.status === "failed";
  const isReady =
    phase === "ready" ||
    status.progress >= 100 ||
    status.review_status === "ai_analyzed" ||
    (status.finding_count > 0 && status.ai_status === "completed");

  return {
    phase: isFailed ? "failed" : isReady ? "ready" : phase,
    label: status.current_step || "Processing…",
    progress: Math.min(100, Math.max(0, status.progress)),
    etaLabel: status.eta_label || (isReady ? "Now" : "~2 min"),
    isProcessing: !isReady && !isFailed,
    isReady,
    isFailed,
    findingCount: status.finding_count ?? 0,
    redlineCount: status.redline_count ?? 0,
  };
}

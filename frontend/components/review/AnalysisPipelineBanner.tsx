"use client";

import React, { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Brain, CheckCircle2, FileSearch, Loader2, RefreshCw } from "lucide-react";
import { useReviewStatus } from "@/services/hooks/useReviews";
import { derivePipelineView } from "@/lib/analysisPipeline";
import { uploadService } from "@/services/api/uploads";
import { reviewService } from "@/services/api/reviews";

interface AnalysisPipelineBannerProps {
  reviewId: string;
  className?: string;
  /** Show template-specific subtitle when source is template_generation */
  showSourceHint?: boolean;
}

export function AnalysisPipelineBanner({
  reviewId,
  className = "",
  showSourceHint = true,
}: AnalysisPipelineBannerProps) {
  const queryClient = useQueryClient();
  const { data: status, isLoading, refetch, isFetching } = useReviewStatus(reviewId, {
    enabled: !!reviewId,
    pollInterval: 2000,
  });
  const wasProcessing = useRef(false);
  const [retrying, setRetrying] = React.useState(false);

  const pipeline = derivePipelineView(status);

  useEffect(() => {
    if (wasProcessing.current && pipeline.isReady) {
      queryClient.invalidateQueries({ queryKey: ["reviews", reviewId] });
      queryClient.invalidateQueries({ queryKey: ["reviews", reviewId, "findings"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", reviewId, "redlines"] });
      queryClient.invalidateQueries({ queryKey: ["contract-detail", reviewId] });
      queryClient.invalidateQueries({ queryKey: ["ai-platform"] });
    }
    wasProcessing.current = pipeline.isProcessing;
  }, [pipeline.isReady, pipeline.isProcessing, queryClient, reviewId]);

  if (isLoading && !status) {
    return (
      <div className={`rounded-lg border border-purple-200 bg-purple-50 dark:bg-purple-900/10 dark:border-purple-800 px-4 py-3 ${className}`}>
        <div className="flex items-center gap-2 text-sm text-purple-800 dark:text-purple-200">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading AI review status…
        </div>
      </div>
    );
  }

  if (pipeline.isReady && !showSourceHint) {
    return null;
  }

  if (pipeline.isReady) {
    return (
      <div className={`rounded-lg border border-green-200 bg-green-50 dark:bg-green-900/10 dark:border-green-800 px-4 py-3 ${className}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-green-800 dark:text-green-200">
                AI review complete — ready for review
              </p>
              <p className="text-xs text-green-700 dark:text-green-300 mt-0.5">
                {pipeline.findingCount} finding{pipeline.findingCount === 1 ? "" : "s"}
                {" · "}
                {pipeline.redlineCount} redline{pipeline.redlineCount === 1 ? "" : "s"} proposed
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const handleRetry = async () => {
    if (!status?.upload_id) return;
    setRetrying(true);
    try {
      if (status.error_code === "ANALYSIS_FAILURE") {
        await reviewService.reAnalyze(reviewId, { analysis_type: "full", review_id: reviewId });
      } else {
        await uploadService.retry(status.upload_id);
      }
      await refetch();
    } finally {
      setRetrying(false);
    }
  };

  if (pipeline.isFailed) {
    return (
      <div className={`rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-800 px-4 py-3 ${className}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-red-800 dark:text-red-200">
                AI review pipeline failed
              </p>
              <p className="text-xs text-red-700 dark:text-red-300 mt-0.5">
                {status?.error || "Ingestion or analysis did not complete."}
              </p>
            </div>
          </div>
          {status?.can_retry && (
            <button
              type="button"
              onClick={handleRetry}
              disabled={retrying}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${retrying ? "animate-spin" : ""}`} />
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  const sourceHint =
    status?.analysis_source === "template_generation"
      ? "Template contract — findings and redlines are generated automatically."
      : "AI review runs automatically after upload.";

  return (
    <div className={`rounded-lg border border-purple-200 bg-purple-50 dark:bg-purple-900/10 dark:border-purple-800 px-4 py-3 ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 min-w-0">
          <div className="flex items-center gap-1.5 flex-shrink-0 mt-0.5">
            {pipeline.phase === "ingesting" ? (
              <FileSearch className="w-5 h-5 text-purple-600 animate-pulse" />
            ) : (
              <Brain className="w-5 h-5 text-purple-600 animate-pulse" />
            )}
            {(isFetching || pipeline.isProcessing) && (
              <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />
            )}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-purple-900 dark:text-purple-100">
              {pipeline.label}
            </p>
            {showSourceHint && (
              <p className="text-xs text-purple-700 dark:text-purple-300 mt-0.5">{sourceHint}</p>
            )}
            <p className="text-[10px] text-purple-600 dark:text-purple-400 mt-1">
              Estimated time remaining: <span className="font-semibold">{pipeline.etaLabel}</span>
              {status?.ingestion_state && (
                <span className="text-purple-500"> · Ingestion: {status.ingestion_state.replace(/_/g, " ")}</span>
              )}
              {status?.ai_status && (
                <span className="text-purple-500"> · AI: {status.ai_status}</span>
              )}
            </p>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <span className="text-lg font-bold text-purple-800 dark:text-purple-200">{pipeline.progress}%</span>
        </div>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-purple-200 dark:bg-purple-900/40">
        <div
          className="h-full rounded-full bg-purple-600 transition-all duration-500"
          style={{ width: `${pipeline.progress}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-center gap-2 text-[9px] text-purple-600 dark:text-purple-400 uppercase tracking-wide">
        <span className={pipeline.phase === "ingesting" || pipeline.phase === "queued" ? "font-bold" : "opacity-50"}>
          Ingest
        </span>
        <span>→</span>
        <span className={pipeline.phase === "analyzing" ? "font-bold" : "opacity-50"}>
          AI findings
        </span>
        <span>→</span>
        <span className={pipeline.phase === "ready" ? "font-bold" : "opacity-50"}>
          Redlines
        </span>
      </div>
    </div>
  );
}

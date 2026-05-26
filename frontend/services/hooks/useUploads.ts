/**
 * Upload query hooks — TanStack Query wrappers for the ingestion API.
 *
 * Handles file upload, status polling, and AI analysis triggers
 * with proper cache invalidation and error handling.
 */

"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { uploadService } from "@/services/api/uploads";
import { reviewKeys } from "@/services/hooks/useReviews";
import type { UploadStatusResponse, UploadResponse } from "@/services/api/client";

// ── Query Key Factory ─────────────────────────────────────────────

export const uploadKeys = {
  all: ["uploads"] as const,
  lists: () => [...uploadKeys.all, "list"] as const,
  list: (params?: { page?: number; page_size?: number }) =>
    [...uploadKeys.lists(), params] as const,
  details: () => [...uploadKeys.all, "detail"] as const,
  detail: (id: string) => [...uploadKeys.details(), id] as const,
  status: (id: string) => [...uploadKeys.all, "status", id] as const,
  chunks: (id: string) => [...uploadKeys.all, "chunks", id] as const,
  analysisRuns: (id: string) => [...uploadKeys.all, "analysis", id] as const,
};

// ── List Uploads ──────────────────────────────────────────────────

export function useUploads(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: uploadKeys.list(params),
    queryFn: () => uploadService.list(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchOnWindowFocus: true,
    retry: 2,
  });
}

// ── Single Upload ─────────────────────────────────────────────────

export function useUpload(uploadId: string | undefined) {
  return useQuery({
    queryKey: uploadKeys.detail(uploadId!),
    queryFn: () => uploadService.get(uploadId!),
    enabled: !!uploadId,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 2,
  });
}

// ── Upload Status (Polling Hook) ──────────────────────────────────
/**
 * Polls upload ingestion status with exponential backoff.
 * Automatically stops when state is REVIEW_READY, FAILED, CANCELLED, or QUARANTINED.
 */
export function useUploadStatus(
  uploadId: string | undefined,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: uploadKeys.status(uploadId!),
    queryFn: () => uploadService.getStatus(uploadId!),
    enabled: !!uploadId && (options?.enabled ?? true),
    refetchInterval: (query) => {
      if (!query.state.data) return 2000;

      const terminalStates = [
        "review_ready", "failed", "cancelled", "quarantined",
      ];
      if (terminalStates.includes(query.state.data.ingestion_state)) {
        return false; // Stop polling
      }

      return 2000; // Poll every 2 seconds during active ingestion
    },
    staleTime: 0,
    gcTime: 30_000,
    retry: 3,
  });
}

// ── Queue Stats ──────────────────────────────────────────────────

export function useQueueStats() {
  return useQuery({
    queryKey: [...uploadKeys.all, "queue-stats"],
    queryFn: () => uploadService.getQueueStats(),
    staleTime: 10_000,
    gcTime: 30_000,
    refetchInterval: 15_000, // Poll every 15 seconds
    retry: 1,
  });
}

// ── Upload Chunks ─────────────────────────────────────────────────

export function useUploadChunks(uploadId: string | undefined) {
  return useQuery({
    queryKey: uploadKeys.chunks(uploadId!),
    queryFn: () => uploadService.listChunks(uploadId!),
    enabled: !!uploadId,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

// ── AI Analysis Runs ──────────────────────────────────────────────

export function useAnalysisRuns(uploadId: string | undefined) {
  return useQuery({
    queryKey: uploadKeys.analysisRuns(uploadId!),
    queryFn: () => uploadService.listAnalysisRuns(uploadId!),
    enabled: !!uploadId,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
  });
}

// ── Mutations ─────────────────────────────────────────────────────

/** Upload a file with cache invalidation */
export function useUploadFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => uploadService.uploadFile(file),

    onSuccess: () => {
      // Invalidate upload lists to show new upload
      queryClient.invalidateQueries({
        queryKey: uploadKeys.lists(),
      });
    },
  });
}

/** Retry a failed upload */
export function useRetryUpload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (uploadId: string) => uploadService.retry(uploadId),

    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: uploadKeys.status(data.upload_id),
      });
      queryClient.invalidateQueries({
        queryKey: uploadKeys.detail(data.upload_id),
      });
    },
  });
}

/** Trigger AI analysis on an upload */
export function useTriggerAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      uploadId,
      analysisType,
    }: {
      uploadId: string;
      analysisType?: "full" | "risk_only" | "redline_only";
    }) => uploadService.analyze(uploadId, analysisType),

    onSuccess: (data) => {
      // Invalidate analysis runs for this upload
      queryClient.invalidateQueries({
        queryKey: uploadKeys.analysisRuns(data.upload_id),
      });
      // Invalidate the upload status (state will change to ANALYSIS_PENDING)
      queryClient.invalidateQueries({
        queryKey: uploadKeys.status(data.upload_id),
      });
    },
  });
}

/** Get or create a review from an upload — bridges upload → review workflow */
export function useGetOrCreateReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (uploadId: string) => uploadService.get(uploadId)
      .then(() => reviewService.getOrCreate(uploadId)),

    onSuccess: (data) => {
      // Cache the new review
      queryClient.setQueryData(
        reviewKeys.detail(data.review_id),
        data,
      );
      // Invalidate review lists and dashboard
      queryClient.invalidateQueries({
        queryKey: reviewKeys.lists(),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.dashboard(),
      });
    },
  });
}

// Need to import reviewService for the mutation above
import { reviewService } from "@/services/api/reviews";

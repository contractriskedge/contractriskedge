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
import {
  getGlobalConnectionState,
  processingInterval,
  usePollCounter,
} from "@/services/hooks/useAdaptivePolling";

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

// ── Upload Status (Adaptive Polling Hook) ─────────────────────────
/**
 * Polls upload ingestion status with WebSocket-aware adaptive polling.
 *
 * Polling strategy:
 * - WebSocket connected → poll every 120s (realtime events drive updates)
 * - WebSocket reconnecting → poll every 10s
 * - WebSocket disconnected/failed → poll every 5s
 * - Active processing → exponential backoff (2s → 3s → 4.5s → ... → 30s max)
 *
 * Automatically stops when state is REVIEW_READY, FAILED, CANCELLED, or QUARANTINED.
 */
export function useUploadStatus(
  uploadId: string | undefined,
  options?: { enabled?: boolean },
) {
  const { pollCount, incrementPollCount, resetPollCount } = usePollCounter();

  return useQuery({
    queryKey: uploadKeys.status(uploadId!),
    queryFn: () => uploadService.getStatus(uploadId!),
    enabled: !!uploadId && (options?.enabled ?? true),
    refetchInterval: (query) => {
      if (!query.state.data) {
        // No data yet — use connection-aware initial interval
        const connState = getGlobalConnectionState();
        if (connState === "connected") return 120_000;
        if (connState === "reconnecting") return 10_000;
        return 5_000;
      }

      const terminalStates = [
        "review_ready", "failed", "cancelled", "quarantined",
      ];
      if (terminalStates.includes(query.state.data.ingestion_state)) {
        resetPollCount();
        return false; // Stop polling
      }

      // Active processing — use exponential backoff
      const isProcessing = !terminalStates.includes(query.state.data.ingestion_state);
      if (isProcessing) {
        incrementPollCount();
        return processingInterval(pollCount);
      }

      // WebSocket-aware fallback
      const connState = getGlobalConnectionState();
      if (connState === "connected") return 120_000;
      if (connState === "reconnecting") return 10_000;
      return 5_000;
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

// ── Batch Upload Query Keys ───────────────────────────────────────

export const batchKeys = {
  all: ["batches"] as const,
  lists: () => [...batchKeys.all, "list"] as const,
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    [...batchKeys.lists(), params] as const,
  details: () => [...batchKeys.all, "detail"] as const,
  detail: (id: string) => [...batchKeys.details(), id] as const,
};

/** List batch uploads */
export function useBatches(params?: { page?: number; page_size?: number; status?: string }) {
  return useQuery({
    queryKey: batchKeys.list(params),
    queryFn: () => uploadService.listBatches(params),
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    refetchOnWindowFocus: true,
  });
}

/** Get batch details with per-file status (polls during active processing) */
export function useBatchDetail(batchId: string | undefined) {
  return useQuery({
    queryKey: batchKeys.detail(batchId!),
    queryFn: () => uploadService.getBatch(batchId!),
    enabled: !!batchId,
    refetchInterval: (query) => {
      if (!query.state.data) return 3000;
      const terminalStates = ["completed", "failed", "cancelled", "partial"];
      if (terminalStates.includes(query.state.data.status)) {
        return false;
      }
      return 3000;
    },
    staleTime: 0,
    gcTime: 30_000,
  });
}

/** Create a new batch upload container */
export function useCreateBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name?: string) => uploadService.createBatch(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: batchKeys.lists() });
    },
  });
}

/** Upload a file to an existing batch */
export function useUploadBatchFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ batchId, file }: { batchId: string; file: File }) =>
      uploadService.uploadBatchFile(batchId, file),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: batchKeys.detail(variables.batchId) });
    },
  });
}

/** Trigger batch processing */
export function useProcessBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (batchId: string) => uploadService.processBatch(batchId),
    onSuccess: (_data, batchId) => {
      queryClient.invalidateQueries({ queryKey: batchKeys.detail(batchId) });
    },
  });
}

/** Cancel a batch */
export function useCancelBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (batchId: string) => uploadService.cancelBatch(batchId),
    onSuccess: (_data, batchId) => {
      queryClient.invalidateQueries({ queryKey: batchKeys.detail(batchId) });
      queryClient.invalidateQueries({ queryKey: batchKeys.lists() });
    },
  });
}

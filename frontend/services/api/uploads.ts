/**
 * Upload API service — typed DTO-based endpoints for the ingestion domain.
 *
 * Provides file upload, status polling, chunk retrieval, and retry flows.
 */

import api, { UploadResponse, UploadStatusResponse, AnalysisRunResponse, PaginatedResponse } from "./client";

// ── DTOs ──────────────────────────────────────────────────────────

export interface UploadInitiateRequest {
  filename: string;
  content_type: string;
  file_size: number;
  client_checksum_sha256?: string;
  metadata?: Record<string, unknown>;
}

export interface UploadInitiateResponse {
  upload_id: string;
  storage_url: string;
  expires_in: number;
  allowed_methods: string[];
  required_headers: Record<string, string>;
}

export interface UploadCompleteRequest {
  upload_id: string;
  client_checksum_sha256?: string;
}

export interface UploadCompleteResponse {
  upload_id: string;
  ingestion_state: string;
  message: string;
}

export interface UploadChunkResponse {
  chunk_id: string;
  chunk_index: number;
  text: string;
  token_count: number;
  page_numbers: number[];
  section_heading: string | null;
  clause_type: string | null;
  checksum: string;
  embedding_status: string;
  similarity_score: number | null;
}

export interface UploadSummary {
  upload_id: string;
  filename: string;
  file_size: number;
  content_type: string;
  ingestion_state: string;
  created_at: string;
}

export interface RetryResponse {
  upload_id: string;
  ingestion_state: string;
  retry_count: number;
  message: string;
}

// ── Service ───────────────────────────────────────────────────────

export const uploadService = {
  /** Upload a file via multipart form */
  uploadFile: (file: File, idempotencyKey?: string) =>
    api.uploadFile<UploadResponse>(
      "/uploads",
      file,
      undefined,
      undefined,
    ),

  /** Get upload metadata and status */
  get: (uploadId: string) =>
    api.get<UploadStatusResponse>(`/uploads/${uploadId}`),

  /** Get ingestion status with progress */
  getStatus: (uploadId: string) =>
    api.get<UploadStatusResponse>(`/uploads/${uploadId}/status`),

  /** List all uploads */
  list: (params?: { page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return api.get<PaginatedResponse<UploadSummary>>(
      `/uploads${qs ? `?${qs}` : ""}`,
    );
  },

  /** Retry a failed upload */
  retry: (uploadId: string) =>
    api.post<RetryResponse>(`/uploads/${uploadId}/retry`),

  /** Get chunks for an upload */
  listChunks: (uploadId: string) =>
    api.get<{ upload_id: string; total_chunks: number; chunks: UploadChunkResponse[] }>(
      `/uploads/${uploadId}/chunks`,
    ),

  // ── AI Analysis ──

  /** Trigger AI analysis on an upload */
  analyze: (
    uploadId: string,
    analysisType: "full" | "risk_only" | "redline_only" = "full",
    idempotencyKey?: string,
  ) =>
    api.post<{ run_id: string; upload_id: string; status: string; message: string }>(
      "/ai/analyze",
      { upload_id: uploadId, analysis_type: analysisType },
      { idempotencyKey },
    ),

  /** Get AI analysis run status */
  getAnalysisRun: (runId: string) =>
    api.get<AnalysisRunResponse>(`/ai/runs/${runId}`),

  /** List all AI analysis runs for an upload */
  listAnalysisRuns: (uploadId: string) =>
    api.get<{ runs: AnalysisRunResponse[]; total: number }>(
      `/ai/runs?upload_id=${uploadId}`,
    ),

  /** Get AI analysis findings */
  getAnalysisFindings: (runId: string) =>
    api.get<{ findings: Array<Record<string, unknown>> }>(
      `/ai/runs/${runId}/findings`,
    ),

  /** Get AI analysis redlines */
  getAnalysisRedlines: (runId: string) =>
    api.get<{ redlines: Array<Record<string, unknown>> }>(
      `/ai/runs/${runId}/redlines`,
    ),

  // ── Queue Stats ──

  /** Get ingestion queue statistics from Redis/Celery */
  getQueueStats: () =>
    api.get<QueueStatsResponse>("/uploads/queue/stats"),

  // ── Batch Uploads ──

  /** Create a new batch upload container */
  createBatch: (name?: string) =>
    api.post<BatchUploadResponse>("/uploads/batch", { name }),

  /** Upload a file to an existing batch */
  uploadBatchFile: (batchId: string, file: File) =>
    api.uploadFile<BatchUploadFileItem>(`/uploads/batch/${batchId}/files`, file),

  /** Get batch details with per-file status */
  getBatch: (batchId: string) =>
    api.get<BatchUploadDetailResponse>(`/uploads/batch/${batchId}`),

  /** List batch uploads */
  listBatches: (params?: { page?: number; page_size?: number; status?: string }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.status) query.set("status", params.status);
    const qs = query.toString();
    return api.get<BatchUploadListResponse>(`/uploads/batches${qs ? `?${qs}` : ""}`);
  },

  /** Trigger processing of all files in a batch */
  processBatch: (batchId: string) =>
    api.post<{ message: string; batch_id: string; total_files: number }>(
      `/uploads/batch/${batchId}/process`,
    ),

  /** Cancel a batch */
  cancelBatch: (batchId: string) =>
    api.post<{ message: string; batch_id: string }>(
      `/uploads/batch/${batchId}/cancel`,
    ),
};

export interface QueueStatsResponse {
  queues: ProcessingQueueInfo[];
  totalPending: number;
  totalProcessing: number;
  totalQueues: number;
  activeQueues: number;
  error?: string;
}

export interface ProcessingQueueInfo {
  id: string;
  name: string;
  status: "active" | "paused" | "idle";
  pendingCount: number;
  processingCount: number;
  completedCount: number;
  failedCount: number;
  throughput: number;
  avgLatency: number;
}

// ── Batch Upload DTOs ─────────────────────────────────────────────

export interface BatchUploadResponse {
  batch_id: string;
  name: string | null;
  status: string;
  total_files: number;
  completed_files: number;
  failed_files: number;
  total_bytes: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface BatchUploadFileItem {
  upload_id: string;
  filename: string;
  file_size: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface BatchUploadDetailResponse extends BatchUploadResponse {
  files: BatchUploadFileItem[];
}

export interface BatchUploadListResponse {
  items: BatchUploadResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

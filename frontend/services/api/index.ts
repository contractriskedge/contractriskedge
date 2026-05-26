/**
 * API services barrel export.
 *
 * Import from this file for all API interactions:
 *
 *   import { reviewService, uploadService, api } from '@/services/api';
 *
 *   const reviews = await reviewService.list({ status: 'in_review' });
 *   const status = await reviewService.getStatus(reviewId);
 *   const upload = await uploadService.uploadFile(file);
 */

export { api, ApiRequestError, NetworkError, TimeoutError } from "./client";
export type {
  ApiError,
  ApiResponse,
  PaginatedResponse,
  ReviewStatusResponse,
  ReviewDetail,
  FindingItem,
  RedlineItem,
  CommentItem,
  UploadStatusResponse,
  UploadResponse,
  AnalysisRunResponse,
  DashboardResponse,
} from "./client";

export { reviewService } from "./reviews";
export type {
  ReviewFilterParams,
  FindingResolveRequest,
  RedlineUpdateRequest,
  CommentCreateRequest,
  AssignRequest,
  EscalateRequest,
  ApproveRequest,
  ReAnalysisRequest,
  ReAnalysisResponse,
} from "./reviews";

export { uploadService } from "./uploads";
export type {
  UploadInitiateRequest,
  UploadInitiateResponse,
  UploadCompleteRequest,
  UploadCompleteResponse,
  UploadChunkResponse,
  UploadSummary,
  RetryResponse,
} from "./uploads";

/**
 * Services barrel export.
 *
 * Single import point for all API services and hooks.
 *
 * Usage:
 *   import { api, reviewService, uploadService, useReviews, useReviewStatus } from '@/services';
 */

export { api, ApiRequestError, NetworkError, TimeoutError } from "./api/client";
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
} from "./api/client";

export { reviewService } from "./api/reviews";
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
} from "./api/reviews";

export { uploadService } from "./api/uploads";
export type {
  UploadInitiateRequest,
  UploadInitiateResponse,
  UploadCompleteRequest,
  UploadCompleteResponse,
  UploadChunkResponse,
  UploadSummary,
  RetryResponse,
} from "./api/uploads";

export {
  useReviews,
  useReview,
  findReviewInQueryCache,
  useReviewStatus,
  useReviewDashboard,
  useReviewFindings,
  useReviewRedlines,
  useReviewComments,
  useReviewHistory,
  useResolveFinding,
  useUpdateRedline,
  useAddComment,
  useAssignReviewer,
  useEscalateReview,
  useApproveReview,
  useUpdateReviewStatus,
  useReAnalyzeReview,
  useDeleteReview,
  reviewKeys,
} from "./hooks/useReviews";

export {
  useUploads,
  useUpload,
  useUploadStatus,
  useUploadChunks,
  useAnalysisRuns,
  useUploadFile,
  useRetryUpload,
  useTriggerAnalysis,
  useGetOrCreateReview,
  uploadKeys,
} from "./hooks/useUploads";
export {
  useWorkspace,
  prefetchWorkspace,
  useWorkspaceRealtime,
  workspaceKeys,
} from "./hooks/useWorkspace";
export type {
  WorkspaceData,
  ReviewStatusHydration,
  DocumentVersionItem,
  ActivityItem,
  RecoveryActionItem,
} from "./hooks/useWorkspace";

export { RealtimeClient, getRealtimeClient, disconnectRealtimeClient } from "@/lib/realtime";
export type { RealtimeEvent, ConnectionState, RealtimeOptions } from "@/lib/realtime";
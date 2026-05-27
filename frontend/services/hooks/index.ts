/**
 * Hooks barrel export.
 *
 * Usage:
 *   import { useReviews, useReview, useReviewStatus, useUploadFile } from '@/services/hooks';
 */

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
  useRiskBreakdown,
  useRiskDeltaTimeline,
  useRiskWaterfall,
  useVersionImpacts,
  useGenerateMitigationRedline,
  reviewKeys,
} from "./useReviews";

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
} from "./useUploads";
export {
  useWorkspace,
  prefetchWorkspace,
  useWorkspaceRealtime,
  workspaceKeys,
} from "./useWorkspace";
export type {
  WorkspaceData,
  ReviewStatusHydration,
  DocumentVersionItem,
  ActivityItem,
  RecoveryActionItem,
} from "./useWorkspace";

export {
  useSystemDiagnostics,
  useEventChain,
  useOutboxDiagnostics,
  useWorkerDiagnostics,
  diagnosticsKeys,
} from "./useDiagnostics";
export type {
  DiagnosticsData,
  EventChainItem,
  OutboxDiagnosticsData,
  WorkerDiagnosticsData,
} from "./useDiagnostics";

export { useRealtime } from "./useRealtime";

export { useSessionGovernance } from "./useSessionGovernance";

export {
  adaptiveInterval,
  processingInterval,
  usePollCounter,
  getGlobalConnectionState,
  setGlobalConnectionState,
} from "./useAdaptivePolling";
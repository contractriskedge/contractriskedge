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

// ── Phase 2: Real data hooks (replacing mockData) ────────────────
export {
  useContracts,
  useContractKpis,
  useContractById,
  useSavedViews,
  contractKeys,
} from "./useContracts";

export {
  useProcurementDashboard,
  useSuppliers,
  useSupplierById,
  procurementKeys,
} from "./useProcurement";

export {
  useComplianceDashboard,
  useComplianceFrameworks,
  useComplianceFindings,
  complianceKeys,
} from "./useCompliance";

export {
  useWorkflowDashboard,
  useWorkflows,
  workflowKeys,
} from "./useWorkflows";

export {
  useBenchmarkDashboard,
  useIndustryBenchmarks,
  benchmarkKeys,
} from "./useBenchmarks";

export {
  useAdminDashboard,
  useAdminUsers,
  useAuditLogs,
  adminKeys,
} from "./useAdmin";

export {
  usePendingExceptions,
  usePendingApprovals,
  useHumanOversightDashboard,
  useDecideApproval,
  useReviewException,
  humanOversightKeys,
} from "./useHumanOversight";

export {
  useAIQualityDashboard,
  usePrompts,
  aiGovernanceKeys,
} from "./useAIGovernance";
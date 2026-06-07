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

export { requestCoalescer, getCoalescerMetrics } from "./requestCoalescer";
export { sessionGovernance } from "./sessionGovernance";

export { policyService, policyKeys } from "./policy";
export type {
  PolicyDefinition,
  PolicyEffect,
  RuleCondition,
  ConditionGroup,
  PolicyEvaluationResult,
  PolicyCreateRequest,
} from "./policy";

export { explainabilityService, explainabilityKeys } from "./explainability";
export type {
  EvidenceChain,
  EvidenceLink,
  AlternativeRecommendation,
  ConfidenceBreakdown,
} from "./explainability";

export { clauseIntelligenceService, clauseIntelligenceKeys } from "./clauseIntelligence";
export type {
  ClauseGraph,
  ClauseNode,
  ClauseEdge,
  ClauseCategory,
  VendorClauseProfile,
} from "./clauseIntelligence";

export { executiveService, executiveKeys } from "./executive";
export type {
  ExecutiveDashboard,
  ExecutiveKPI,
  TrendData,
  RiskHeatmap,
  Bottleneck,
  Forecast,
} from "./executive";

export { tenantService, tenantKeys } from "./tenant";
export type {
  TenantSettingsResponse,
  TenantSettingsUpdate,
  TenantConfiguration,
  TenantBranding,
  WorkflowDefinition,
  FeatureFlagDefinition,
  FeatureFlagEvaluation,
  FeatureFlagOverride,
  PolicyPackResponse,
  ScoringOverrideResponse,
  CompliancePackResponse,
  TenantSummary,
} from "./tenant";
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

// ── Phase 2: Real API services (replacing mockData) ──────────────
export {
  fetchContracts,
  fetchContractKpis,
  fetchContractById,
  fetchSavedViews,
} from "./contracts";
export type {
  ContractsListResponse,
  ContractsKpiResponse,
} from "./contracts";

export {
  fetchProcurementDashboard,
  fetchSuppliers,
  fetchSupplierById,
} from "./procurement";
export type {
  ProcurementDashboardData,
  ProcurementKpi,
  SupplierRecord,
} from "./procurement";

export {
  fetchComplianceDashboard,
  fetchComplianceFindings,
} from "./compliance";
export type {
  ComplianceDashboardData,
  ComplianceKpi,
  ComplianceFinding,
} from "./compliance";

export {
  fetchWorkflowDashboard,
  fetchWorkflows,
} from "./workflows";
export type {
  WorkflowDashboardData,
  WorkflowKpi,
  WorkflowRecord,
} from "./workflows";

export {
  fetchBenchmarkDashboard,
  fetchIndustryBenchmarks,
} from "./benchmarks";
export type {
  BenchmarkDashboardData,
  BenchmarkKpi,
  ClauseBenchmark,
  IndustryCorpus,
} from "./benchmarks";

export {
  fetchAdminDashboard,
  fetchAdminUsers,
  fetchAuditLogs,
} from "./admin";
export type {
  AdminDashboardData,
  AdminKpi,
  AdminUser,
  AdminAuditEvent,
} from "./admin";

export {
  fetchPendingExceptions,
  fetchPendingApprovals,
  fetchHumanOversightDashboard,
} from "./humanOversight";
export type {
  ApprovalSummary,
  PolicyExceptionRequest,
  HumanOversightDashboard,
} from "./humanOversight";

export {
  fetchAIQualityDashboard,
  fetchPrompts,
  aiGovernanceKeys,
} from "./aiGovernance";
export type {
  AIQualityDashboard,
  PromptSummary,
  ModelUsageSummary,
} from "./aiGovernance";

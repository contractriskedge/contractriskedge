/**
 * Enterprise AI Review Platform — barrel exports.
 */

export { EnterpriseReviewPlatform } from "./EnterpriseReviewPlatform";
export { ReviewContextProvider, useReviewContext } from "./ReviewContext";
export { DocumentViewer } from "./DocumentViewer";
export { FindingsSection } from "./FindingsSection";
export { PolicyIssuesSection } from "./PolicyIssuesSection";
export { RecommendationsSection } from "./RecommendationsSection";
export { WorkflowSection } from "./WorkflowSection";
export { AuditTrailSection } from "./AuditTrailSection";
export { RedlineWorkspace } from "./RedlineWorkspace";
export { ReviewSummarySection } from "./ReviewSummarySection";
export { ExplainabilitySection } from "./ExplainabilitySection";
export { VersionsSection } from "./VersionsSection";
export { RiskReductionSection } from "./RiskReductionSection";
export type * from "./types";
export {
  useReviews,
  useReview,
  useFindings,
  usePolicyViolations,
  useMissingClauses,
  useRecommendations,
  useWorkflow,
  useActivity,
  useComments,
  useReviewerWorkloads,
  useQueueMetrics,
  useAssignReview,
  useApproveReview,
  useRejectReview,
  useSubmitReviewDecision,
  useSubmitFeedback,
  useResolveFinding,
  useApplyRecommendation,
  useDismissRecommendation,
  useAddComment,
  useAdvanceWorkflow,
  useVersions,
  useRiskBreakdownData,
  useReviewRedlinesData,
  platformKeys,
} from "./hooks";

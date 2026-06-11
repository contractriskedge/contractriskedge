/**
 * Enterprise AI Review Platform — comprehensive type system.
 *
 * Strict semantic color system:
 * - Blue: informational / system
 * - Amber: warning / medium risk
 * - Red: critical / high risk / error
 * - Green: success / resolved / mitigated
 * - Gray: neutral / neutral / dismissed
 */

import type { RiskLevel } from "@/components/dashboard/contracts/types";

// ── Semantic Color System ───────────────────────────────────────────────────

export type SemanticColor = "critical" | "high" | "medium" | "low" | "info" | "success" | "warning" | "neutral";

export const SEMANTIC_COLORS: Record<string, { bg: string; text: string; border: string; dot: string; badge: string }> = {
  critical: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", dot: "bg-red-500", badge: "bg-red-100 text-red-700" },
  high:      { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", dot: "bg-red-500", badge: "bg-red-100 text-red-700" },
  medium:    { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", dot: "bg-amber-500", badge: "bg-amber-100 text-amber-700" },
  low:       { bg: "bg-gray-50", text: "text-gray-600", border: "border-gray-200", dot: "bg-gray-400", badge: "bg-gray-100 text-gray-600" },
  info:      { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", dot: "bg-blue-500", badge: "bg-blue-100 text-blue-700" },
  success:   { bg: "bg-green-50", text: "text-green-700", border: "border-green-200", dot: "bg-green-500", badge: "bg-green-100 text-green-700" },
  warning:   { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", dot: "bg-amber-500", badge: "bg-amber-100 text-amber-700" },
  neutral:   { bg: "bg-gray-50", text: "text-gray-600", border: "border-gray-200", dot: "bg-gray-400", badge: "bg-gray-100 text-gray-600" },
};

export function severityColor(severity: string): typeof SEMANTIC_COLORS[string] {
  return SEMANTIC_COLORS[severity] || SEMANTIC_COLORS.neutral;
}

// ── Review ──────────────────────────────────────────────────────────────────

export interface ReviewSummary {
  review_id: string;
  contract_name: string;
  contract_number: string | null;
  original_filename: string | null;
  vendor: string;
  document_type: string;
  status: ReviewStatus;
  workflow_stage: string;
  risk_score: number | null;
  risk_level: RiskLevel;
  priority: "low" | "medium" | "high" | "critical";
  assigned_to: string | null;
  assigned_to_name: string | null;
  finding_count: number;
  critical_findings: number;
  high_findings: number;
  policy_violations: number;
  missing_clauses: number;
  sla_status: SlaStatus;
  sla_deadline: string | null;
  overdue_hours: number;
  escalation_level: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  age_hours: number;
  computed_status?: string;
}

export type ReviewStatus =
  | "draft"
  | "ai_analyzed"
  | "under_review"
  | "legal_review"
  | "procurement_review"
  | "security_review"
  | "escalated"
  | "approved"
  | "rejected"
  | "archived";

export type SlaStatus = "on_track" | "warning" | "overdue" | "critical_overdue";

// ── Finding (with inline explainability) ────────────────────────────────────

export interface Finding {
  finding_id: string;
  title: string;
  description: string;
  severity: RiskLevel;
  confidence: number;
  clause_type: string;
  clause_text: string;
  page_numbers: number[];
  category: string;
  status: FindingStatus;
  resolution: string | null;
  resolution_type: string | null;
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  business_impact: string | null;
  recommended_mitigation: string | null;
  // Inline explainability
  reasoning: string | null;
  similarity_score: number | null;
  benchmark_deviation: number | null;
  matched_corpus: string | null;
  confidence_semantic: number | null;
  confidence_structural: number | null;
  confidence_linguistic: number | null;
  confidence_reference: number | null;
  supporting_evidence: string[];
  alternative_interpretations: string[];
  // Feedback
  feedback: AiFeedback | null;
  feedback_type: string | null;
}

export type FindingStatus = "open" | "acknowledged" | "resolved" | "dismissed" | "false_positive" | "accepted" | "rejected" | "modified" | "waived" | "escalated" | "mitigated";

// ── AI Feedback Loop ────────────────────────────────────────────────────────

export interface AiFeedback {
  feedback_id: string;
  finding_id: string;
  type: "correct" | "incorrect" | "partial" | "unsure";
  reviewer_note: string;
  correction_category: string | null;
  correction_detail: string | null;
  created_at: string;
  created_by: string;
  retraining_priority: "low" | "medium" | "high";
  retraining_status: "pending" | "queued" | "completed" | "declined";
}

// ── Policy Violation ────────────────────────────────────────────────────────

export interface PolicyViolation {
  id: string;
  policy_name: string;
  policy_version?: string;
  clause_type: string;
  severity: RiskLevel;
  description?: string;
  expected?: string;
  actual?: string;
  recommendation?: string;
  page_number?: number;
  compliance_impact?: "critical" | "high" | "medium" | "low" | "none";
  regulation?: string;
  status: "open" | "waived" | "resolved";
  created_at?: string;
  // New end-to-end fields from the policy engine pipeline
  finding_id?: string;
  finding_title?: string;
  finding_description?: string;
  rule_id?: string;
  playbook_id?: string;
  rule_description?: string;
  effect?: string;
  is_mandatory?: boolean;
  waiver_status?: "pending" | "approved" | "rejected" | "expired";
  waiver_justification?: string;
  waiver_requested_by?: string;
  waiver_requested_at?: string;
}

// ── Missing Clause ──────────────────────────────────────────────────────────

export interface MissingClause {
  id: string;
  clause_type: string;
  importance: "required" | "recommended" | "optional";
  reason: string;
  risk_if_missing: string;
  fallback_recommendation: string;
  industry_standard: boolean;
}

// ── Recommendation ──────────────────────────────────────────────────────────

export interface Recommendation {
  recommendation_id: string;
  type: "remediation" | "negotiation" | "fallback" | "best_practice";
  clause_type: string;
  title: string;
  description: string;
  suggested_text: string | null;
  rationale: string;
  confidence: number;
  impact: "high" | "medium" | "low";
  effort: "high" | "medium" | "low";
  priority: number;
  status: "pending" | "applied" | "dismissed";
  finding_id: string | null;
}

// ── Workflow ────────────────────────────────────────────────────────────────

export interface WorkflowState {
  current_stage: string;
  available_actions: string[];
  stages: WorkflowStage[];
  sla_remaining_hours: number;
  escalation_level: number;
  reviewers: Reviewer[];
  queue_position: number;
  queue_total: number;
  workload_score: number;
}

export interface WorkflowStage {
  id: string;
  label: string;
  status: "completed" | "current" | "pending" | "skipped" | "rejected";
  completed_at?: string;
  completed_by?: string;
  sla_deadline?: string;
}

export interface Reviewer {
  user_id: string;
  name: string;
  email: string;
  role: string;
  assigned_at: string;
  active_reviews: number;
  workload_pct: number;
}

// ── Activity / Audit ────────────────────────────────────────────────────────

export type ActivityType =
  | "review_created"
  | "ai_analysis_completed"
  | "finding_resolved"
  | "finding_dismissed"
  | "finding_feedback"
  | "comment_added"
  | "review_assigned"
  | "review_approved"
  | "review_rejected"
  | "review_escalated"
  | "status_changed"
  | "re_analysis"
  | "version_created"
  | "policy_waived"
  | "recommendation_applied";

export interface ActivityEvent {
  id: string;
  type: ActivityType;
  actor: string;
  actor_initials: string;
  action: string;
  details: string | null;
  timestamp: string;
  /** Previous state value before the action (e.g. "open", "proposed") */
  before_state?: string | null;
  /** New state value after the action (e.g. "resolved", "accepted") */
  after_state?: string | null;
  /** Type of object that changed (e.g. "finding", "redline", "review") */
  object_type?: string | null;
  /** ID of the object that changed */
  object_id?: string | null;
  metadata?: Record<string, unknown>;
}

// ── Collaboration ───────────────────────────────────────────────────────────

export interface Comment {
  comment_id: string;
  review_id: string;
  finding_id: string | null;
  author: string;
  author_initials: string;
  content: string;
  mentions: string[];
  parent_id: string | null;
  replies: Comment[];
  status: "active" | "resolved";
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
}

// ── Reviewer Workload ───────────────────────────────────────────────────────

export interface ReviewerWorkload {
  user_id: string;
  name: string;
  email: string;
  active_reviews: number;
  completed_today: number;
  overdue_reviews: number;
  avg_review_time_hours: number;
  workload_pct: number;
  sla_breaches: number;
  role: string;
}

// ── SLA / Queue Metrics ─────────────────────────────────────────────────────

export interface QueueMetrics {
  total: number;
  unassigned: number;
  in_review: number;
  overdue: number;
  critical_overdue: number;
  escalated: number;
  sla_at_risk: number;
  avg_age_hours: number;
  max_age_hours: number;
  completed_today: number;
}

// ── Unified Review Context ──────────────────────────────────────────────────

export interface ReviewContextState {
  selectedReviewId: string | null;
  selectedReview: ReviewSummary | null;
  findings: Finding[];
  policyViolations: PolicyViolation[];
  missingClauses: MissingClause[];
  recommendations: Recommendation[];
  workflow: WorkflowState | null;
  activity: ActivityEvent[];
  comments: Comment[];
  activeSection: ReviewSection;
  selectedFindingId: string | null;
  expandedFindingId: string | null;
  showLeftPanel: boolean;
  showRightPanel: boolean;
  isLoading: boolean;
  isFindingsLoading: boolean;
  isPolicyLoading: boolean;
  isRecommendationsLoading: boolean;
  isWorkflowLoading: boolean;
  isActivityLoading: boolean;
  error: string | null;
}

export type ReviewSection = "summary" | "overview" | "findings" | "redline" | "versions" | "policy" | "recommendations" | "risk_reduction" | "workflow" | "explainability" | "audit" | "governance" | "history" | "obligations";

// ── Keyboard Shortcuts ──────────────────────────────────────────────────────

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  description: string;
  action: string;
}

/**
 * Review API service — typed DTO-based endpoints for the review domain.
 *
 * All functions return typed responses via the centralized API client.
 * No direct fetch() calls. All errors are normalized ApiRequestError instances.
 */

import api, {
  ReviewDetail,
  normalizeReviewDetail,
  ReviewStatusResponse,
  FindingItem,
  RedlineItem,
  CommentItem,
  DashboardResponse,
  PaginatedResponse,
  WorkloadMetrics,
  BulkActionResponse,
  DocumentVersionItem,
  RiskBreakdown,
  MyWorkItem,
  RecommendationItem,
} from "./client";

// ── DTOs ──────────────────────────────────────────────────────────

export interface ReviewFilterParams {
  status?: string;
  assigned_to?: string;
  priority?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface FindingResolveRequest {
  resolution:
    | "acknowledged"
    | "resolved"
    | "dismissed"
    | "false_positive"
    | "escalated";
  note?: string;
}

export interface RedlineUpdateRequest {
  status: "accepted" | "rejected" | "modified";
  modified_text?: string;
  review_notes?: string;
}

export interface CommentCreateRequest {
  entity_type?: string;
  entity_id?: string;
  parent_comment_id?: string;
  body: string;
  mentions?: string[];
}

export interface AssignRequest {
  assignee_id: string;
  role?: "reviewer" | "approver" | "observer";
  due_date?: string;
}

export interface EscalateRequest {
  reason: string;
  escalated_to?: string;
  raise_priority?: boolean;
  target_workflow_stage?: string;
}

export interface ApproveRequest {
  decision: "approved" | "rejected" | "conditionally_approved";
  comments?: string;
  conditions?: Record<string, unknown>;
}

export interface ReAnalysisRequest {
  review_id: string;
  analysis_type?: "full" | "risk_only" | "redline_only";
  reason?: string;
}

export interface ReAnalysisResponse {
  review_id: string;
  run_id: string;
  status: string;
  message: string;
  previous_run_id: string | null;
  version: number;
}

export interface ReviewDeleteRequest {
  reason?: string;
}

export interface ReviewArchiveRequest {
  older_than_days: number;
  status_filter?: string;
  dry_run?: boolean;
}

export interface BulkAssignRequest {
  review_ids: string[];
  assignee_id: string;
  role?: string;
  due_date?: string;
}

export interface BulkEscalateRequest {
  review_ids: string[];
  reason: string;
  escalated_to?: string;
}

export interface BulkApproveRequest {
  review_ids: string[];
  decision?: string;
  comments?: string;
}

// ── Service ───────────────────────────────────────────────────────

export const reviewService = {
  /** List reviews with filtering and pagination */
  list: (params?: ReviewFilterParams) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.assigned_to) query.set("assigned_to", params.assigned_to);
    if (params?.priority) query.set("priority", params.priority);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.sort_order) query.set("sort_order", params.sort_order);
    const qs = query.toString();
    return api.get<PaginatedResponse<ReviewDetail>>(
      qs ? `/reviews/?${qs}` : "/reviews/",
    );
  },

  /** Get a single review by ID */
  get: async (reviewId: string) => {
    const raw = await api.get<unknown>(`/reviews/${reviewId}`);
    return normalizeReviewDetail(raw);
  },

  /** Get review status for frontend polling */
  getStatus: (reviewId: string) =>
    api.get<ReviewStatusResponse>(`/reviews/${reviewId}/status`),

  /** Update review status */
  updateStatus: (
    reviewId: string,
    status: string,
    reason?: string,
    idempotencyKey?: string,
  ) => {
    const query = new URLSearchParams({ status });
    if (reason) query.set("reason", reason);
    return api.post<Record<string, unknown>>(
      `/reviews/${reviewId}/status?${query}`,
      undefined,
      { idempotencyKey },
    );
  },

  /** Get or create a review from an upload */
  getOrCreate: async (uploadId: string) => {
    const raw = await api.get<unknown>(`/reviews/upload/${uploadId}`);
    return normalizeReviewDetail(raw);
  },

  // ── Findings ──

  /** List findings for a review */
  listFindings: (
    reviewId: string,
    params?: { severity?: string; resolution?: string; page?: number; page_size?: number },
  ) => {
    const query = new URLSearchParams();
    if (params?.severity) query.set("severity", params.severity);
    if (params?.resolution) query.set("resolution", params.resolution);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return api.get<{ findings: FindingItem[]; total: number; page: number; page_size: number }>(
      `/reviews/${reviewId}/findings${qs ? `?${qs}` : ""}`,
    );
  },

  /** Resolve a finding */
  resolveFinding: (
    reviewId: string,
    findingId: string,
    body: FindingResolveRequest,
    idempotencyKey?: string,
  ) =>
    api.post<Record<string, unknown>>(
      `/reviews/${reviewId}/findings/${findingId}/resolve`,
      body,
      { idempotencyKey },
    ),

  // ── Redlines ──

  /** List redlines for a review */
  listRedlines: (reviewId: string, status?: string) => {
    const qs = status ? `?status=${status}` : "";
    return api.get<{ redlines: RedlineItem[] }>(
      `/reviews/${reviewId}/redlines${qs}`,
    );
  },

  /** Regenerate a redline using the finding's category as mandatory filter */
  regenerateRedline: (
    reviewId: string,
    body: {
      finding_id: string;
      finding_category: string;
      redline_id: string;
    },
  ) =>
    api.post<{
      redline_id: string;
      clause_type: string;
      proposed_text: string;
      rationale: string | null;
      risk_level: string | null;
      status: string;
      finding_id: string;
      finding_category: string;
      finding_title: string;
      message: string;
    }>(`/reviews/${reviewId}/regenerate-redline`, body),

  /** Get risk score breakdown by clause category */
  getRiskBreakdown: (reviewId: string) =>
    api.get<RiskBreakdown>(`/reviews/${reviewId}/risk-breakdown`),

  /** Get risk delta timeline — every decision that changed risk */
  getRiskDeltaTimeline: (reviewId: string) =>
    api.get<{ review_id: string; delta_count: number; deltas: Record<string, unknown>[] }>(
      `/reviews/${reviewId}/risk-delta-timeline`,
    ),

  /** Get risk waterfall chart data — original → decisions → remaining */
  getRiskWaterfall: (reviewId: string) =>
    api.get<{ original_risk: number; current_risk: number; segments: Record<string, unknown>[] }>(
      `/reviews/${reviewId}/risk-waterfall`,
    ),

  /** Get version impacts — risk changes grouped by document version */
  getVersionImpacts: (reviewId: string) =>
    api.get<{ review_id: string; version_count: number; impacts: Record<string, unknown>[] }>(
      `/reviews/${reviewId}/version-impacts`,
    ),

  /** Generate a redline from a mitigation recommendation (closed-loop remediation) */
  generateMitigationRedline: (
    reviewId: string,
    body: {
      mitigation_type: string;
      clause_category: string;
      finding_ids?: string[];
    },
  ) =>
    api.post<{
      redline_id: string;
      clause_type: string | null;
      proposed_text: string;
      rationale: string | null;
      risk_level: string | null;
      status: string;
      traceability: Record<string, unknown> | null;
      finding_ids: string[];
      mitigation_type: string;
      mitigation_label: string;
      estimated_reduction_pct: number;
      confidence: number;
      duplicate?: boolean;
      existing?: boolean;
    }>(`/reviews/${reviewId}/generate-mitigation-redline`, body),

  /** Update a redline (accept/reject/modify) */
  updateRedline: (
    reviewId: string,
    redlineId: string,
    body: RedlineUpdateRequest,
    idempotencyKey?: string,
  ) =>
    api.put<Record<string, unknown>>(
      `/reviews/${reviewId}/redlines/${redlineId}`,
      body,
      { idempotencyKey },
    ),

  // ── Comments ──

  /** List comments on a review */
  listComments: (reviewId: string) =>
    api.get<{ comments: CommentItem[] }>(`/reviews/${reviewId}/comments`),

  /** Add a comment */
  addComment: (
    reviewId: string,
    body: CommentCreateRequest,
    idempotencyKey?: string,
  ) =>
    api.post<Record<string, unknown>>(
      `/reviews/${reviewId}/comments`,
      body,
      { idempotencyKey },
    ),

  // ── Workflow Actions ──

  /** Assign a reviewer */
  assign: (reviewId: string, body: AssignRequest, idempotencyKey?: string) =>
    api.post<Record<string, unknown>>(
      `/reviews/${reviewId}/assign`,
      body,
      { idempotencyKey },
    ),

  /** Escalate a review */
  escalate: (reviewId: string, body: EscalateRequest, idempotencyKey?: string) =>
    api.post<Record<string, unknown>>(
      `/reviews/${reviewId}/escalate`,
      body,
      { idempotencyKey },
    ),

  /** Toggle favorite status */
  toggleFavorite: (reviewId: string, isFavorite: boolean) =>
    api.post<{ review_id: string; is_favorite: boolean }>(
      `/reviews/${reviewId}/favorite`,
      { is_favorite: isFavorite },
    ),

  /** Approve/reject a review */
  approve: (reviewId: string, body: ApproveRequest, idempotencyKey?: string) =>
    api.post<Record<string, unknown>>(
      `/reviews/${reviewId}/approve`,
      body,
      { idempotencyKey },
    ),

  /** Finalize an approved review */
  finalize: (reviewId: string) =>
    api.post<Record<string, unknown>>(`/reviews/${reviewId}/finalize`),

  /** Get status change history */
  getHistory: (reviewId: string) =>
    api.get<{ history: Array<{ from_status: string; to_status: string; changed_by: string; reason: string | null; created_at: string }> }>(
      `/reviews/${reviewId}/history`,
    ),

  /** Waive a policy violation. */
  waivePolicyViolation: (reviewId: string, body: {
    rule_id: string;
    justification: string;
    risk_assessment?: string;
    proposed_alternative?: string;
  }) =>
    api.post<{ override_id: string; status: string; requested_at: string }>(
      `/reviews/${reviewId}/policy-violations/waive`,
      body,
    ),

  // ── Dashboard ──

  /** Get review dashboard aggregation */
  getDashboard: () =>
    api.get<DashboardResponse>("/reviews/dashboard"),

  // ── Reviewer Ops ──

  /** Get My Work — reviews assigned to current user */
  getMyWork: () =>
    api.get<MyWorkItem[]>("/reviews/my-work"),

  /** Get Queue — operational review workbench with filters */
  getQueue: (params?: {
    status?: string;
    assigned_to?: string;
    risk_min?: number;
    risk_max?: number;
    age_min_hours?: number;
    age_max_hours?: number;
    escalated_only?: boolean;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: "asc" | "desc";
  }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.assigned_to) query.set("assigned_to", params.assigned_to);
    if (params?.risk_min !== undefined) query.set("risk_min", String(params.risk_min));
    if (params?.risk_max !== undefined) query.set("risk_max", String(params.risk_max));
    if (params?.age_min_hours !== undefined) query.set("age_min_hours", String(params.age_min_hours));
    if (params?.age_max_hours !== undefined) query.set("age_max_hours", String(params.age_max_hours));
    if (params?.escalated_only) query.set("escalated_only", "true");
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.sort_order) query.set("sort_order", params.sort_order);
    const qs = query.toString();
    return api.get<PaginatedResponse<ReviewDetail>>(
      qs ? `/reviews/queue?${qs}` : "/reviews/queue",
    );
  },

  /** Get AI Recommendations from review findings */
  getRecommendations: (params?: {
    severity?: string;
    clause_type?: string;
    min_confidence?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.severity) query.set("severity", params.severity);
    if (params?.clause_type) query.set("clause_type", params.clause_type);
    if (params?.min_confidence !== undefined) query.set("min_confidence", String(params.min_confidence));
    if (params?.limit) query.set("limit", String(params.limit));
    const qs = query.toString();
    return api.get<RecommendationItem[]>(
      qs ? `/reviews/recommendations?${qs}` : "/reviews/recommendations",
    );
  },

  // ── Re-analysis ──

  /** Trigger re-analysis on an existing review */
  reAnalyze: (reviewId: string, body?: Partial<ReAnalysisRequest>, idempotencyKey?: string) =>
    api.post<ReAnalysisResponse>(
      `/reviews/${reviewId}/re-analyze`,
      body || { review_id: reviewId },
      { idempotencyKey },
    ),

  // ── Soft Delete & Archive ──

  /** Soft-delete a review */
  softDelete: (reviewId: string, body?: ReviewDeleteRequest, idempotencyKey?: string) =>
    api.delete<{ review_id: string; status: string; message: string }>(
      `/reviews/${reviewId}`,
      { idempotencyKey, body },
    ),

  /** Archive old reviews */
  archive: (body: ReviewArchiveRequest) =>
    api.post<{ archived_count: number; dry_run: boolean; message: string }>(
      "/reviews/archive",
      body,
    ),

  // ── Workload Metrics ──

  /** Get workload metrics */
  getWorkloadMetrics: () =>
    api.get<WorkloadMetrics>("/reviews/workload/metrics"),

  /** Get per-reviewer workload snapshot */
  getReviewersWorkload: () =>
    api.get<{
      reviewers: Array<{
        user_id: string;
        name: string;
        email: string;
        role: string;
        active_reviews: number;
        completed_today: number;
        overdue_reviews: number;
        avg_review_time_hours: number;
        workload_pct: number;
        sla_breaches: number;
      }>;
    }>("/reviews/reviewers/workload"),

  // ── Routing ──

  /** Apply routing rules to a single review */
  applyRouting: (reviewId: string) =>
    api.post<{ matched: boolean; action: Record<string, unknown> }>(
      `/reviews/routing/apply/${reviewId}`,
    ),

  /** Apply routing rules to all unassigned reviews */
  applyRoutingAll: () =>
    api.post<{ total: number; routed: number }>("/reviews/routing/apply-all"),

  // ── Bulk Operations ──

  /** Bulk assign reviews */
  bulkAssign: (body: BulkAssignRequest) =>
    api.post<BulkActionResponse>("/reviews/bulk/assign", body),

  /** Bulk escalate reviews */
  bulkEscalate: (body: BulkEscalateRequest) =>
    api.post<BulkActionResponse>("/reviews/bulk/escalate", body),

  /** Bulk approve reviews */
  bulkApprove: (body: BulkApproveRequest) =>
    api.post<BulkActionResponse>("/reviews/bulk/approve", body),

  /** Bulk export reviews as CSV */
  bulkExport: async (reviewIds: string[]) => {
    const response = await fetch(`/api/v1/reviews/bulk/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ review_ids: reviewIds }),
    });
    if (!response.ok) throw new Error("Export failed");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reviews_export_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  // ── Document Versions ──

  /** List all document versions for a review */
  listVersions: (reviewId: string) =>
    api.get<DocumentVersionItem[]>(`/reviews/${reviewId}/versions`),

  /** Create a new document version */
  createVersion: (reviewId: string, body: {
    label?: string;
    change_summary?: string;
    accepted_redline_ids?: string[];
  }) =>
    api.post<DocumentVersionItem>(`/reviews/${reviewId}/versions`, body),

  /** Get structured clause-level diff between two versions */
  diffVersions: (reviewId: string, versionIdA: string, versionIdB: string) =>
    api.get<{ version_a: any; version_b: any; changes: any[]; total_changes: number }>(
      `/reviews/${reviewId}/versions/${versionIdA}/diff/${versionIdB}`,
    ),

  // ── Exports ──

  /** Export negotiation package as ZIP download */
  exportNegotiationPackage: (reviewId: string) =>
    api.downloadFile(
      `/reviews/${reviewId}/export-negotiation-package`,
      `negotiation_package_${reviewId.slice(0, 8)}_${new Date().toISOString().slice(0, 10)}.zip`,
      "application/zip",
    ),

  /** Export review audit/memo as ZIP download */
  exportReviewAudit: (reviewId: string) =>
    api.downloadFile(
      `/reviews/${reviewId}/export-audit`,
      `review_audit_${reviewId.slice(0, 8)}_${new Date().toISOString().slice(0, 10)}.zip`,
      "application/zip",
    ),

  /** Download a document version (.docx) with auth headers */
  downloadVersion: (reviewId: string, versionId: string, filename?: string) =>
    api.downloadFile(
      `/reviews/${reviewId}/versions/${versionId}/download`,
      filename ||
        `contract_${reviewId.slice(0, 8)}_${new Date().toISOString().slice(0, 10)}.docx`,
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),

  /** Export tracked-changes DOCX with redlines as visual markup */
  exportTrackedChanges: (reviewId: string, versionId: string) =>
    api.downloadFile(
      `/reviews/${reviewId}/versions/${versionId}/export-tracked`,
      `tracked_changes_${reviewId.slice(0, 8)}_${new Date().toISOString().slice(0, 10)}.docx`,
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),

  /** Export executive summary as ZIP download */
  exportExecutiveSummary: (reviewId: string) =>
    api.downloadFile(
      `/reviews/${reviewId}/export-executive-summary`,
      `executive_summary_${reviewId.slice(0, 8)}_${new Date().toISOString().slice(0, 10)}.zip`,
      "application/zip",
    ),
};

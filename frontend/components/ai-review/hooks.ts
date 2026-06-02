/**
 * Enterprise AI Review Platform — API hooks layer.
 *
 * Provides TanStack Query hooks for all review operations.
 * Falls back to seeded mock data when backend is unavailable.
 * Controlled by NEXT_PUBLIC_USE_MOCK_DATA env var.
 *
 * Required APIs:
 * - GET /reviews
 * - GET /reviews/{id}
 * - GET /reviews/{id}/findings
 * - GET /reviews/{id}/recommendations
 * - GET /reviews/{id}/policy-violations
 * - GET /reviews/{id}/workflow
 * - GET /reviews/{id}/explainability
 * - POST /reviews/{id}/assign
 * - POST /reviews/{id}/approve
 * - POST /reviews/{id}/reject
 * - POST /reviews/{id}/feedback
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiRequestError } from "@/services/api/client";

// ── Mock data control ───────────────────────────────────────────────────────
// Set NEXT_PUBLIC_USE_MOCK_DATA=false to disable mock fallbacks in production.
// When false, API errors will propagate and show error states instead of mock data.

const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA !== "false";

import {
  MOCK_REVIEWS,
  MOCK_FINDINGS,
  MOCK_POLICY_VIOLATIONS,
  MOCK_MISSING_CLAUSES,
  MOCK_RECOMMENDATIONS,
  MOCK_WORKFLOW_STATES,
  MOCK_ACTIVITY,
  MOCK_COMMENTS,
  MOCK_REVIEWERS,
  MOCK_QUEUE_METRICS,
  MOCK_VERSIONS,
  MOCK_RISK_BREAKDOWN,
  MOCK_REDLINES,
} from "./mockData";
import type {
  ReviewSummary,
  Finding,
  FindingStatus,
  PolicyViolation,
  MissingClause,
  Recommendation,
  WorkflowState,
  ActivityEvent,
  Comment,
  ReviewerWorkload,
  QueueMetrics,
  AiFeedback,
} from "./types";
import type { RiskLevel } from "@/components/dashboard/contracts/types";
import type { MockDocumentVersion, MockRiskBreakdown, MockRedlineItem } from "./mockData";

// ── API → UI normalization (backend uses paginated ReviewDetail shape) ─────

type ApiRecord = Record<string, unknown>;

function friendlyDocumentType(raw: string): string {
  if (!raw) return "Contract";
  if (raw.includes("wordprocessingml")) return "DOCX";
  if (raw.includes("pdf")) return "PDF";
  if (raw.length > 40) return "Contract";
  return raw;
}

function normalizeRiskScore(score: number | null | undefined): number | null {
  if (score == null || Number.isNaN(Number(score))) return null;
  const n = Number(score);
  return n <= 1 ? Math.round(n * 100) / 10 : n;
}

function riskLevelFromScore(score: number | null | undefined): RiskLevel {
  const n = normalizeRiskScore(score ?? null);
  if (n == null) return "medium";
  if (n >= 8) return "critical";
  if (n >= 6) return "high";
  if (n >= 4) return "medium";
  return "low";
}

export function mapApiReviewToSummary(raw: ApiRecord): ReviewSummary {
  const reviewId = String(raw.review_id ?? "");
  const contractName = String(
    raw.document_name ?? raw.original_filename ?? raw.contract_name ?? "Untitled",
  );
  const riskScore = normalizeRiskScore(
    raw.risk_score != null ? Number(raw.risk_score) : null,
  );

  return {
    review_id: reviewId,
    contract_name: contractName,
    vendor: String(raw.vendor ?? raw.counterparty ?? ""),
    document_type: friendlyDocumentType(String(raw.document_type ?? "")),
    status: String(raw.status ?? "draft") as ReviewSummary["status"],
    workflow_stage: String(raw.workflow_stage ?? raw.status ?? "draft"),
    risk_score: riskScore,
    risk_level: riskLevelFromScore(raw.risk_score != null ? Number(raw.risk_score) : null),
    priority: (String(raw.priority ?? "medium") as ReviewSummary["priority"]),
    assigned_to: raw.assigned_to ? String(raw.assigned_to) : null,
    assigned_to_name: raw.assigned_to_name ? String(raw.assigned_to_name) : null,
    finding_count: Number(raw.finding_count ?? 0),
    critical_findings: Number(raw.critical_findings ?? 0),
    high_findings: Number(raw.high_findings ?? 0),
    policy_violations: Number(raw.policy_violations ?? 0),
    missing_clauses: Number(raw.missing_clauses ?? 0),
    sla_status: (String(raw.sla_status ?? "on_track") as ReviewSummary["sla_status"]),
    sla_deadline: raw.sla_deadline ? String(raw.sla_deadline) : null,
    overdue_hours: Number(raw.overdue_hours ?? 0),
    escalation_level: Number(raw.escalation_level ?? raw.escalation_count ?? 0),
    created_at: String(raw.created_at ?? ""),
    updated_at: String(raw.updated_at ?? ""),
    completed_at: raw.completed_at ? String(raw.completed_at) : null,
    age_hours: 0,
  };
}

function findingStatusFromResolution(resolution: unknown): FindingStatus {
  if (!resolution) return "open";
  const r = String(resolution);
  if (r === "resolved") return "resolved";
  if (r === "dismissed" || r === "false_positive") return "dismissed";
  if (r === "acknowledged") return "acknowledged";
  return "open";
}

export function mapApiFinding(raw: ApiRecord): Finding {
  const description = String(raw.description ?? "");
  return {
    finding_id: String(raw.finding_id ?? raw.id ?? ""),
    title: String(raw.title ?? "Finding"),
    description,
    severity: (String(raw.severity ?? "medium") as Finding["severity"]),
    confidence: Number(raw.confidence ?? 0),
    clause_type: String(raw.clause_type ?? "other"),
    clause_text: String(raw.clause_text ?? description),
    page_numbers: Array.isArray(raw.page_numbers) ? (raw.page_numbers as number[]) : [],
    category: String(raw.category ?? raw.clause_type ?? "other"),
    status: findingStatusFromResolution(raw.resolution ?? raw.status),
    resolution: raw.resolution ? String(raw.resolution) : null,
    resolution_type: raw.resolution_type ? String(raw.resolution_type) : null,
    created_at: String(raw.created_at ?? ""),
    resolved_at: raw.resolved_at ? String(raw.resolved_at) : null,
    resolved_by: raw.resolved_by ? String(raw.resolved_by) : null,
    business_impact: raw.business_impact ? String(raw.business_impact) : null,
    recommended_mitigation: String(raw.recommendation ?? raw.recommended_mitigation ?? ""),
    reasoning: raw.reasoning ? String(raw.reasoning) : description,
    similarity_score: raw.similarity_score != null ? Number(raw.similarity_score) : null,
    benchmark_deviation: raw.benchmark_deviation != null ? Number(raw.benchmark_deviation) : null,
    matched_corpus: raw.matched_corpus ? String(raw.matched_corpus) : null,
    confidence_semantic: null,
    confidence_structural: null,
    confidence_linguistic: null,
    confidence_reference: null,
    supporting_evidence: [],
    alternative_interpretations: [],
    feedback: null,
  };
}

function extractReviewRows(res: ApiRecord): ApiRecord[] {
  if (Array.isArray(res.data)) return res.data as ApiRecord[];
  if (Array.isArray(res.reviews)) return res.reviews as ApiRecord[];
  if (Array.isArray(res.items)) return res.items as ApiRecord[];
  return [];
}

function isNotFoundError(err: unknown): boolean {
  return err instanceof ApiRequestError && err.status_code === 404;
}

/** Backend sub-routes not yet in review/router.py — skip fetch to avoid 404 console noise. */
export const REVIEW_SUBRESOURCE_API = {
  policyViolations: false,
  missingClauses: false,
  recommendations: false,
  workflow: false,
  activity: false,
  document: false,
  reviewersWorkload: false,
  metrics: false,
} as const;

type ReviewSubresourceKey = keyof typeof REVIEW_SUBRESOURCE_API;

async function fetchReviewSubresource<T>(
  key: ReviewSubresourceKey,
  fetcher: () => Promise<T>,
  mockFallback: T,
): Promise<T> {
  if (!REVIEW_SUBRESOURCE_API[key]) {
    if (USE_MOCK_DATA) return mockFallback;
    return (Array.isArray(mockFallback) ? [] : null) as T;
  }
  try {
    return await fetcher();
  } catch (err) {
    if (isNotFoundError(err)) {
      return (Array.isArray(mockFallback) ? [] : null) as T;
    }
    if (!USE_MOCK_DATA) throw err;
    return mockFallback;
  }
}

function optionalSubresourceRetry(count: number, err: unknown): boolean {
  return !isNotFoundError(err) && count < 1;
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const platformKeys = {
  all: ["ai-platform"] as const,
  reviews: () => [...platformKeys.all, "reviews"] as const,
  review: (id: string) => [...platformKeys.all, "review", id] as const,
  findings: (id: string) => [...platformKeys.all, "findings", id] as const,
  policyViolations: (id: string) => [...platformKeys.all, "policy", id] as const,
  missingClauses: (id: string) => [...platformKeys.all, "missing", id] as const,
  recommendations: (id: string) => [...platformKeys.all, "recommendations", id] as const,
  workflow: (id: string) => [...platformKeys.all, "workflow", id] as const,
  activity: (id: string) => [...platformKeys.all, "activity", id] as const,
  comments: (id: string) => [...platformKeys.all, "comments", id] as const,
  reviewers: () => [...platformKeys.all, "reviewers"] as const,
  metrics: () => [...platformKeys.all, "metrics"] as const,
  versions: (id: string) => [...platformKeys.all, "versions", id] as const,
  riskBreakdown: (id: string) => [...platformKeys.all, "risk-breakdown", id] as const,
  redlines: (id: string) => [...platformKeys.all, "redlines", id] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

/** Fetch all reviews with queue metrics. */
export function useReviews() {
  return useQuery({
    queryKey: platformKeys.reviews(),
    queryFn: async () => {
      try {
        const res = await api.get<ApiRecord>("/reviews?page_size=100");
        return extractReviewRows(res).map(mapApiReviewToSummary);
      } catch (err) {
        if (!USE_MOCK_DATA) throw err;
        return MOCK_REVIEWS;
      }
    },
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

/** Fetch a single review by ID. */
export function useReview(reviewId: string) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: platformKeys.review(reviewId),
    queryFn: async () => {
      const fromList = queryClient
        .getQueryData<ReviewSummary[]>(platformKeys.reviews())
        ?.find((r) => r.review_id === reviewId);
      if (fromList) return fromList;

      try {
        const raw = await api.get<ApiRecord>(`/reviews/${reviewId}`);
        return mapApiReviewToSummary(raw);
      } catch (err) {
        if (isNotFoundError(err)) {
          const contractRaw = await api
            .get<ApiRecord>(`/contracts/${reviewId}`)
            .catch(() => null);
          if (contractRaw) return mapApiReviewToSummary({ ...contractRaw, review_id: reviewId });
          return null;
        }
        if (!USE_MOCK_DATA) throw err;
        return MOCK_REVIEWS.find((r) => r.review_id === reviewId) || null;
      }
    },
    enabled: !!reviewId,
    placeholderData: () =>
      queryClient
        .getQueryData<ReviewSummary[]>(platformKeys.reviews())
        ?.find((r) => r.review_id === reviewId),
    staleTime: 30_000,
    retry: (count, err) => !isNotFoundError(err) && count < 2,
  });
}

/** Fetch findings for a review (with inline explainability). */
export function useFindings(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.findings(reviewId),
    queryFn: async () => {
      try {
        const res = await api.get<{ findings: ApiRecord[] }>(`/reviews/${reviewId}/findings`);
        return (res.findings ?? []).map(mapApiFinding);
      } catch (err) {
        if (isNotFoundError(err)) return [];
        if (!USE_MOCK_DATA) throw err;
        return MOCK_FINDINGS;
      }
    },
    enabled: !!reviewId,
    staleTime: 15_000,
  });
}

/** Fetch policy violations for a review. */
export function usePolicyViolations(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.policyViolations(reviewId),
    queryFn: () =>
      fetchReviewSubresource(
        "policyViolations",
        async () => {
          const res = await api.get<{ violations: PolicyViolation[] }>(
            `/reviews/${reviewId}/policy-violations`,
          );
          return res.violations ?? [];
        },
        MOCK_POLICY_VIOLATIONS,
      ),
    enabled: !!reviewId,
    staleTime: 30_000,
    retry: optionalSubresourceRetry,
  });
}

/** Fetch missing clauses for a review. */
export function useMissingClauses(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.missingClauses(reviewId),
    queryFn: () =>
      fetchReviewSubresource(
        "missingClauses",
        async () => {
          const res = await api.get<{ missing_clauses: MissingClause[] }>(
            `/reviews/${reviewId}/missing-clauses`,
          );
          return res.missing_clauses ?? [];
        },
        MOCK_MISSING_CLAUSES,
      ),
    enabled: !!reviewId,
    staleTime: 30_000,
    retry: optionalSubresourceRetry,
  });
}

/** Fetch recommendations for a review. */
export function useRecommendations(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.recommendations(reviewId),
    queryFn: () =>
      fetchReviewSubresource(
        "recommendations",
        async () => {
          const res = await api.get<{ recommendations: Recommendation[] }>(
            `/reviews/${reviewId}/recommendations`,
          );
          return res.recommendations ?? [];
        },
        MOCK_RECOMMENDATIONS,
      ),
    enabled: !!reviewId,
    staleTime: 30_000,
    retry: optionalSubresourceRetry,
  });
}

/** Fetch workflow state for a review. */
export function useWorkflow(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.workflow(reviewId),
    queryFn: () =>
      fetchReviewSubresource(
        "workflow",
        () => api.get<WorkflowState>(`/reviews/${reviewId}/workflow`),
        MOCK_WORKFLOW_STATES[reviewId] || MOCK_WORKFLOW_STATES[Object.keys(MOCK_WORKFLOW_STATES)[0]!]!,
      ),
    enabled: !!reviewId,
    staleTime: 15_000,
    retry: optionalSubresourceRetry,
  });
}

/** Fetch activity events for a review. */
export function useActivity(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.activity(reviewId),
    queryFn: () =>
      fetchReviewSubresource(
        "activity",
        async () => {
          const res = await api.get<{ events: ActivityEvent[] }>(`/reviews/${reviewId}/activity`);
          return res.events ?? [];
        },
        MOCK_ACTIVITY,
      ),
    enabled: !!reviewId,
    staleTime: 15_000,
    refetchInterval: REVIEW_SUBRESOURCE_API.activity ? 60_000 : false,
    retry: optionalSubresourceRetry,
  });
}

/** Fetch comments for a review. */
export function useComments(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.comments(reviewId),
    queryFn: async () => {
      try {
        const res = await api.get<{ comments: Comment[] }>(`/reviews/${reviewId}/comments`);
        return res.comments ?? [];
      } catch (err) {
        if (isNotFoundError(err)) return [];
        if (!USE_MOCK_DATA) throw err;
        return MOCK_COMMENTS;
      }
    },
    enabled: !!reviewId,
    staleTime: 15_000,
    retry: optionalSubresourceRetry,
  });
}

/** Fetch reviewer workloads. */
export function useReviewerWorkloads() {
  return useQuery({
    queryKey: platformKeys.reviewers(),
    queryFn: () =>
      fetchReviewSubresource(
        "reviewersWorkload",
        async () => {
          const res = await api.get<{ reviewers: ReviewerWorkload[] }>("/reviews/reviewers/workload");
          return res.reviewers ?? [];
        },
        MOCK_REVIEWERS,
      ),
    staleTime: 60_000,
    retry: optionalSubresourceRetry,
  });
}

/** Fetch queue metrics. */
export function useQueueMetrics() {
  return useQuery({
    queryKey: platformKeys.metrics(),
    queryFn: () =>
      fetchReviewSubresource(
        "metrics",
        () => api.get<QueueMetrics>("/reviews/metrics"),
        MOCK_QUEUE_METRICS,
      ),
    staleTime: 30_000,
    refetchInterval: REVIEW_SUBRESOURCE_API.metrics ? 60_000 : false,
    retry: optionalSubresourceRetry,
  });
}

/** Fetch document versions for a review. */
export function useVersions(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.versions(reviewId),
    queryFn: async () => {
      try {
        const res = await api.get<any>(`/reviews/${reviewId}/versions`);
        // Backend returns a plain array, but may also wrap in { versions: [...] }
        if (Array.isArray(res)) return res;
        if (res && Array.isArray(res.versions)) return res.versions;
        if (res && Array.isArray(res.data)) return res.data;
        console.warn("Unexpected versions response format", res);
        return [];
      } catch (err) {
        if (!USE_MOCK_DATA) throw err;
        return MOCK_VERSIONS;
      }
    },
    enabled: !!reviewId,
    staleTime: 15_000,
  });
}

/** Fetch risk breakdown for a review. */
export function useRiskBreakdownData(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.riskBreakdown(reviewId),
    queryFn: async () => {
      try {
        return await api.get<MockRiskBreakdown>(`/reviews/${reviewId}/risk-breakdown`);
      } catch (err) {
        if (!USE_MOCK_DATA) throw err;
        return MOCK_RISK_BREAKDOWN;
      }
    },
    enabled: !!reviewId,
    staleTime: 15_000,
  });
}

/** Fetch redlines for a review. */
export function useReviewRedlinesData(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.redlines(reviewId),
    queryFn: async () => {
      try {
        const res = await api.get<{ redlines: MockRedlineItem[] }>(`/reviews/${reviewId}/redlines`);
        return res.redlines;
      } catch (err) {
        if (!USE_MOCK_DATA) throw err;
        return MOCK_REDLINES;
      }
    },
    enabled: !!reviewId,
    staleTime: 15_000,
  });
}

// ── Mutations ───────────────────────────────────────────────────────────────

/** Assign a review to a reviewer. */
export function useAssignReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, assigneeId, note }: { reviewId: string; assigneeId: string; note?: string }) =>
      api.post(`/reviews/${reviewId}/assign`, { assignee_id: assigneeId, note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.all });
    },
  });
}

/** Approve a review. */
export function useApproveReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, comments }: { reviewId: string; comments?: string }) =>
      api.post(`/reviews/${reviewId}/approve`, { comments }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.all });
    },
  });
}

/** Reject a review. */
export function useRejectReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, reason }: { reviewId: string; reason: string }) =>
      api.post(`/reviews/${reviewId}/reject`, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.all });
    },
  });
}

/** Submit AI feedback for a finding. */
export function useSubmitFeedback() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, findingId, feedback }: { reviewId: string; findingId: string; feedback: Partial<AiFeedback> }) =>
      api.post(`/reviews/${reviewId}/feedback`, { finding_id: findingId, ...feedback }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.all });
    },
  });
}

/** Resolve a finding. */
export function useResolveFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, findingId, resolution }: { reviewId: string; findingId: string; resolution: string }) =>
      api.post(`/reviews/${reviewId}/findings/${findingId}/resolve`, { resolution }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: platformKeys.findings(variables.reviewId) });
      queryClient.invalidateQueries({ queryKey: platformKeys.activity(variables.reviewId) });
    },
  });
}

/** Apply a recommendation. */
export function useApplyRecommendation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, recommendationId }: { reviewId: string; recommendationId: string }) =>
      api.post(`/reviews/${reviewId}/recommendations/${recommendationId}/apply`),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: platformKeys.recommendations(variables.reviewId) });
    },
  });
}

/** Dismiss a recommendation. */
export function useDismissRecommendation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, recommendationId }: { reviewId: string; recommendationId: string }) =>
      api.post(`/reviews/${reviewId}/recommendations/${recommendationId}/dismiss`),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: platformKeys.recommendations(variables.reviewId) });
    },
  });
}

/** Add a comment. */
export function useAddComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, content, mentions, findingId }: { reviewId: string; content: string; mentions?: string[]; findingId?: string }) =>
      api.post(`/reviews/${reviewId}/comments`, { content, mentions, finding_id: findingId }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: platformKeys.comments(variables.reviewId) });
      queryClient.invalidateQueries({ queryKey: platformKeys.activity(variables.reviewId) });
    },
  });
}

/** Advance workflow stage. */
export function useAdvanceWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, action }: { reviewId: string; action: string }) =>
      api.post(`/reviews/${reviewId}/workflow/advance`, { action }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: platformKeys.workflow(variables.reviewId) });
      queryClient.invalidateQueries({ queryKey: platformKeys.reviews() });
    },
  });
}

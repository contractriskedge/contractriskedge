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

import { useMemo } from "react";
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
  ActivityType,
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
    feedback_type: raw.feedback_type ? String(raw.feedback_type) : null,
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
  recommendations: true,
  workflow: true,
  activity: true,
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
          const res = await api.get<{ recommendations: ApiRecord[] }>(
            `/reviews/${reviewId}/recommendations`,
          );
          return (res.recommendations ?? []).map(mapApiRecommendation);
        },
        MOCK_RECOMMENDATIONS,
      ),
    enabled: !!reviewId,
    staleTime: 30_000,
    retry: optionalSubresourceRetry,
  });
}

function mapApiRecommendation(raw: ApiRecord): Recommendation {
  const severity = String(raw.severity ?? "medium");
  const impactMap: Record<string, "high" | "medium" | "low"> = {
    critical: "high", high: "high", medium: "medium", low: "low", info: "low",
  };
  const confidence = Number(raw.confidence ?? 0);
  const isResolved = raw.status === "resolved" || raw.resolution != null;

  return {
    recommendation_id: String(raw.recommendation_id ?? `rec-${String(raw.finding_id ?? "").slice(0, 8)}`),
    type: "remediation",
    clause_type: String(raw.clause_type ?? "other"),
    title: String(raw.title ?? "Recommendation"),
    description: String(raw.description ?? ""),
    suggested_text: String(raw.recommendation ?? null),
    rationale: String(raw.recommendation ?? ""),
    confidence: confidence,
    impact: impactMap[severity] ?? "medium",
    effort: confidence >= 0.8 ? "low" : confidence >= 0.5 ? "medium" : "high",
    priority: severity === "critical" ? 1 : severity === "high" ? 2 : severity === "medium" ? 3 : 4,
    status: isResolved ? "applied" : "pending",
    finding_id: String(raw.finding_id ?? null),
  };
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

function extractRawActivityList(data: unknown): ApiRecord[] {
  if (!data) return [];
  if (Array.isArray(data)) return data as ApiRecord[];
  if (typeof data !== "object" || data === null) return [];

  const record = data as ApiRecord;
  if (Array.isArray(record.events)) return record.events as ApiRecord[];

  const nested = record.data;
  if (nested && typeof nested === "object") {
    const inner = nested as ApiRecord;
    if (Array.isArray(inner.events)) return inner.events as ApiRecord[];
    if (Array.isArray(inner)) return inner as ApiRecord[];
  }
  return [];
}

function isMappedActivityEvent(item: ApiRecord): boolean {
  return (
    typeof item.id === "string" &&
    item.id.length > 0 &&
    typeof item.action === "string" &&
    typeof item.type === "string" &&
    typeof item.timestamp === "string" &&
    !("event_type" in item)
  );
}

/** Build audit rows from resolved/dismissed findings when the server audit log is empty. */
function findingsToActivityEvents(findings: Finding[]): ActivityEvent[] {
  return findings
    .filter((f) => f.status === "resolved" || f.status === "dismissed")
    .map((f, index) => {
      const actor = f.resolved_by || "Reviewer";
      const dismissed = f.status === "dismissed";
      return {
        id: `finding-${f.finding_id || index}-${f.status}`,
        type: dismissed ? "finding_dismissed" : "finding_resolved",
        actor,
        actor_initials: actor.charAt(0).toUpperCase() || "?",
        action: dismissed
          ? `Dismissed finding: ${f.title}`
          : `Resolved finding: ${f.title}`,
        details: f.resolution_type
          ? `Resolution: ${f.resolution_type.replace(/_/g, " ")}`
          : f.description || null,
        timestamp: f.resolved_at || f.updated_at || f.created_at || new Date().toISOString(),
        object_type: "finding",
        object_id: f.finding_id,
      };
    })
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

const MOCK_ACTIVITY_IDS = new Set(MOCK_ACTIVITY.map((e) => e.id));

function isSampleActivityList(events: ActivityEvent[]): boolean {
  return events.length > 0 && events.every((e) => MOCK_ACTIVITY_IDS.has(e.id));
}

export type AuditTrailDataSource = "api" | "finding-derived" | "sample" | "none";

/** Normalize activity from API, query cache, or mock (array or `{ events: [] }`). */
export function normalizeActivityEvents(data: unknown): ActivityEvent[] {
  const rawList = extractRawActivityList(data);
  if (rawList.length === 0) return [];

  return rawList.map((raw, index) => {
    if (isMappedActivityEvent(raw)) {
      return raw as unknown as ActivityEvent;
    }
    return mapApiActivityEvent(raw, index);
  });
}

function mapHistoryToActivity(raw: {
  from_status: string;
  to_status: string;
  changed_by: string;
  reason: string | null;
  created_at: string;
}): ActivityEvent {
  const actor = raw.changed_by || "System";
  return {
    id: `hist-${raw.created_at}-${raw.to_status}`,
    type: "status_changed",
    actor,
    actor_initials: actor.charAt(0).toUpperCase() || "?",
    action: `Status changed to ${raw.to_status.replace(/_/g, " ")}`,
    details: raw.reason || `From ${raw.from_status} to ${raw.to_status}`,
    timestamp: raw.created_at,
    before_state: raw.from_status,
    after_state: raw.to_status,
  };
}

function mergeActivityEvents(primary: ActivityEvent[], supplemental: ActivityEvent[]): ActivityEvent[] {
  const seen = new Set(primary.map((e) => e.id));
  const merged = [...primary];
  for (const event of supplemental) {
    if (!seen.has(event.id)) {
      merged.push(event);
      seen.add(event.id);
    }
  }
  return merged.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );
}

async function fetchActivityForReview(reviewId: string): Promise<ActivityEvent[]> {
  try {
    const res = await api.get<ApiRecord>(`/reviews/${reviewId}/activity`);
    return normalizeActivityFromApiResponse(res);
  } catch (err) {
    if (isNotFoundError(err)) {
      return [];
    }
    if (!USE_MOCK_DATA) throw err;
    return MOCK_ACTIVITY;
  }
}

function normalizeActivityFromApiResponse(res: ApiRecord): ActivityEvent[] {
  return normalizeActivityEvents(res);
}

/** Fetch activity events for a review. */
export function useActivity(reviewId: string) {
  return useQuery({
    queryKey: platformKeys.activity(reviewId),
    queryFn: () =>
      fetchReviewSubresource(
        "activity",
        () => fetchActivityForReview(reviewId),
        MOCK_ACTIVITY,
      ),
    enabled: !!reviewId,
    staleTime: 15_000,
    refetchInterval: REVIEW_SUBRESOURCE_API.activity ? 60_000 : false,
    retry: optionalSubresourceRetry,
  });
}

function mapCommentToActivity(comment: Comment, index: number): ActivityEvent {
  return {
    id: `comment-${comment.comment_id || index}`,
    type: "comment_added",
    actor: comment.author,
    actor_initials: comment.author_initials,
    action: comment.finding_id ? "Comment on finding" : "Review comment",
    details: comment.content,
    timestamp: comment.created_at,
    object_type: comment.finding_id ? "finding" : "review",
    object_id: comment.finding_id,
  };
}

/** Single source of truth for audit tab badge + timeline (activity + history + comments). */
export function useAuditTrailEvents(reviewId: string, findings: Finding[] = []) {
  const activityQuery = useActivity(reviewId);
  const { data: comments = [], isLoading: commentsLoading } = useComments(reviewId);

  const historyQuery = useQuery({
    queryKey: [...platformKeys.all, "audit-history", reviewId] as const,
    queryFn: async () => {
      try {
        return await api.get<{
          history: Array<{
            from_status: string;
            to_status: string;
            changed_by: string;
            reason: string | null;
            created_at: string;
          }>;
        }>(`/reviews/${reviewId}/history`);
      } catch (err) {
        if (isNotFoundError(err)) return { history: [] };
        throw err;
      }
    },
    enabled: !!reviewId,
    staleTime: 15_000,
    retry: optionalSubresourceRetry,
  });

  const { events, dataSource, hadSampleFallback } = useMemo(() => {
    const rawApi = normalizeActivityEvents(activityQuery.data);
    const hadSample = isSampleActivityList(rawApi);
    let merged = hadSample ? [] : rawApi;
    let source: AuditTrailDataSource = merged.length > 0 ? "api" : "none";

    const histEvents = (historyQuery.data?.history ?? []).map(mapHistoryToActivity);
    merged = mergeActivityEvents(merged, histEvents);
    if (merged.length > 0 && source === "none") source = "api";

    const commentEvents = comments.map(mapCommentToActivity);
    merged = mergeActivityEvents(merged, commentEvents);

    const beforeFindings = merged.length;
    const fromFindings = findingsToActivityEvents(findings);
    if (fromFindings.length > 0) {
      merged = mergeActivityEvents(merged, fromFindings);
      if (beforeFindings === 0) {
        source = "finding-derived";
      }
    }

    if (merged.length === 0) {
      source = "none";
    } else if (hadSample && source === "finding-derived") {
      source = "finding-derived";
    } else if (hadSample && merged.length > 0) {
      source = "api";
    }

    return { events: merged, dataSource: source, hadSampleFallback: hadSample };
  }, [activityQuery.data, historyQuery.data, comments, findings]);

  return {
    events,
    dataSource,
    hadSampleFallback,
    isSampleData: hadSampleFallback && events.length === 0,
    isLoading: activityQuery.isLoading || historyQuery.isLoading || commentsLoading,
    isFetching: activityQuery.isFetching || historyQuery.isFetching,
    error: activityQuery.error ?? historyQuery.error,
  };
}

function mapApiActivityEvent(raw: ApiRecord, index = 0): ActivityEvent {
  const eventType = String(raw.event_type ?? "unknown");
  const createdAt = String(raw.created_at ?? "");
  const eventId = raw.event_id != null && String(raw.event_id).trim() !== ""
    ? String(raw.event_id)
    : `${eventType}-${createdAt || "t"}-${index}`;
  return {
    id: eventId,
    type: mapActivityType(eventType),
    actor: String(raw.actor_id ?? "System"),
    actor_initials: String(raw.actor_id ?? "S").charAt(0).toUpperCase() || "?",
    action: String(raw.action ?? eventType),
    details: String(raw.description ?? ""),
    timestamp: createdAt || new Date().toISOString(),
    before_state: raw.before_state != null ? String(raw.before_state) : null,
    after_state: raw.after_state != null ? String(raw.after_state) : null,
  };
}

function mapActivityType(eventType: string): ActivityType {
  const t = eventType.toLowerCase();
  if (t.includes("review_created") || t.endsWith(".created")) return "review_created";
  if (t.includes("ai_analysis") || t.includes("ai.copilot") || t.includes("analyzed")) {
    return "ai_analysis_completed";
  }
  if (t.includes("dismissed")) return "finding_dismissed";
  if (t.includes("feedback")) return "finding_feedback";
  if (t.includes("finding")) return "finding_resolved";
  if (t.includes("comment")) return "comment_added";
  if (t.includes("assign")) return "review_assigned";
  if (t.includes("approv")) return "review_approved";
  if (t.includes("reject")) return "review_rejected";
  if (t.includes("escalat")) return "review_escalated";
  if (t.includes("re_analysis") || t.includes("reanalysis")) return "re_analysis";
  if (t.includes("version") || t.includes("document")) return "version_created";
  if (t.includes("recommendation")) return "recommendation_applied";
  if (t.includes("waiv")) return "policy_waived";
  if (t.includes("status") || t.includes("review.")) return "status_changed";
  return "status_changed";
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
      api.post(`/reviews/${reviewId}/findings/${findingId}/feedback`, {
        type: feedback.type,
        reviewer_note: feedback.reviewer_note || "",
        retraining_priority: feedback.retraining_priority || "medium",
      }),
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
      queryClient.invalidateQueries({ queryKey: platformKeys.review(variables.reviewId) });
      queryClient.invalidateQueries({ queryKey: platformKeys.reviews() });
      queryClient.invalidateQueries({ queryKey: platformKeys.riskBreakdown(variables.reviewId) });
      queryClient.invalidateQueries({ queryKey: platformKeys.metrics() });
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
      queryClient.invalidateQueries({ queryKey: platformKeys.findings(variables.reviewId) });
      queryClient.invalidateQueries({ queryKey: platformKeys.activity(variables.reviewId) });
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
      queryClient.invalidateQueries({ queryKey: platformKeys.activity(variables.reviewId) });
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
    mutationFn: ({ reviewId, action, assignee_id, note }: { reviewId: string; action: string; assignee_id?: string; note?: string }) =>
      api.post(`/reviews/${reviewId}/workflow/advance`, { action, assignee_id, note }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: platformKeys.workflow(variables.reviewId) });
      queryClient.invalidateQueries({ queryKey: platformKeys.review(variables.reviewId) });
      queryClient.invalidateQueries({ queryKey: platformKeys.reviews() });
    },
  });
}

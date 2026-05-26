/**
 * Review query hooks — TanStack Query wrappers for the review API.
 *
 * All hooks provide:
 * - Typed responses
 * - Automatic caching and deduplication
 * - Stale-while-revalidate pattern
 * - Background refetching
 * - Error normalization
 * - Request deduplication across components
 *
 * Usage:
 *   const { data, isLoading, error } = useReviews({ status: 'in_review' });
 *   const { data: review } = useReview(reviewId);
 *   const { data: status } = useReviewStatus(reviewId); // auto-polling
 */

"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
  type QueryClient,
} from "@tanstack/react-query";
import { reviewService } from "@/services/api/reviews";
import type {
  ReviewFilterParams,
  FindingResolveRequest,
  RedlineUpdateRequest,
  CommentCreateRequest,
  AssignRequest,
  EscalateRequest,
  ApproveRequest,
  ReAnalysisRequest,
  ReAnalysisResponse,
} from "@/services/api/reviews";
import type {
  ReviewDetail,
  ReviewStatusResponse,
  FindingItem,
  RedlineItem,
  CommentItem,
  DashboardResponse,
  PaginatedResponse,
} from "@/services/api/client";

/** Resolve a review row from list/queue caches while the detail query is in flight. */
export function findReviewInQueryCache(
  queryClient: QueryClient,
  reviewId: string,
): ReviewDetail | undefined {
  const cached = queryClient.getQueryData<ReviewDetail>(reviewKeys.detail(reviewId));
  if (cached?.review_id) return cached;

  const queue = queryClient.getQueryData<PaginatedResponse<ReviewDetail>>([
    "reviews",
    "queue",
  ]);
  const fromQueue = queue?.data?.find((r) => r.review_id === reviewId);
  if (fromQueue) return fromQueue;

  for (const [, page] of queryClient.getQueriesData<PaginatedResponse<ReviewDetail>>({
    queryKey: reviewKeys.lists(),
  })) {
    const hit = page?.data?.find((r) => r.review_id === reviewId);
    if (hit) return hit;
  }
  return undefined;
}

// ── Query Key Factory ─────────────────────────────────────────────
// Centralized key management for cache invalidation

export const reviewKeys = {
  all: ["reviews"] as const,
  lists: () => [...reviewKeys.all, "list"] as const,
  list: (filters: ReviewFilterParams) =>
    [...reviewKeys.lists(), filters] as const,
  details: () => [...reviewKeys.all, "detail"] as const,
  detail: (id: string) => [...reviewKeys.details(), id] as const,
  status: (id: string) => [...reviewKeys.all, "status", id] as const,
  findings: (id: string) => [...reviewKeys.all, "findings", id] as const,
  redlines: (id: string) => [...reviewKeys.all, "redlines", id] as const,
  comments: (id: string) => [...reviewKeys.all, "comments", id] as const,
  history: (id: string) => [...reviewKeys.all, "history", id] as const,
  dashboard: () => [...reviewKeys.all, "dashboard"] as const,
};

// ── List Reviews ──────────────────────────────────────────────────

export function useReviews(filters: ReviewFilterParams = {}) {
  return useQuery({
    queryKey: reviewKeys.list(filters),
    queryFn: () => reviewService.list(filters),
    placeholderData: keepPreviousData,
    staleTime: 30_000, // 30 seconds before considered stale
    gcTime: 5 * 60_000, // 5 minutes in garbage collection
    refetchOnWindowFocus: true,
    retry: 2,
  });
}

// ── Single Review ─────────────────────────────────────────────────

export function useReview(reviewId: string | undefined) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: reviewKeys.detail(reviewId!),
    queryFn: () => reviewService.get(reviewId!),
    enabled: Boolean(reviewId?.trim()),
    placeholderData: () =>
      reviewId ? findReviewInQueryCache(queryClient, reviewId) : undefined,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 2,
  });
}

// ── Review Status (Polling Hook) ──────────────────────────────────
/**
 * Polls the review status endpoint with exponential backoff.
 *
 * Automatically stops polling when:
 * - Status is "completed" (progress === 100)
 * - Status is "failed" and not retryable
 * - Component unmounts
 *
 * Exposes progress, current_step, error for UI rendering.
 */
export function useReviewStatus(
  reviewId: string | undefined,
  options?: {
    pollInterval?: number; // Starting poll interval in ms (default: 2000)
    enabled?: boolean;
  },
) {
  return useQuery({
    queryKey: reviewKeys.status(reviewId!),
    queryFn: async (): Promise<ReviewStatusResponse> => {
      const status = await reviewService.getStatus(reviewId!);

      // Throw on terminal failure (not retryable) to stop polling
      if (
        status.status === "failed" &&
        !status.can_retry &&
        status.error_code
      ) {
        throw new Error(status.error || "Review processing failed");
      }

      return status;
    },
    enabled: !!reviewId && (options?.enabled ?? true),
    // Exponential backoff polling: starts at 2s, maxes at 30s
    refetchInterval: (query) => {
      if (!query.state.data) return (options?.pollInterval ?? 2000);

      const { status, progress, can_retry, review_status } = query.state.data;

      // Terminal states — stop polling entirely
      const terminalStatuses = ["completed", "failed", "approved", "rejected", "closed"];
      if (terminalStatuses.includes(status)) return false;

      // Review has reached a stable post-analysis state — stop polling
      const stableReviewStatuses = ["ai_analyzed", "under_review", "legal_review", "procurement_review", "security_review", "escalated"];
      if (review_status && stableReviewStatuses.includes(review_status)) return false;

      // Stop polling on non-retryable failure
      if (status === "failed" && !can_retry) return false;
      if (progress === 100) return false;

      // Exponential backoff based on progress
      if (progress < 25) return 2000;  // Every 2s during early stages
      if (progress < 50) return 3000;  // Every 3s during mid stages
      if (progress < 75) return 4000;  // Every 4s during later stages
      return 5000;                      // Every 5s near completion
    },
    staleTime: 0, // Always consider status stale (we want fresh polls)
    gcTime: 30_000,
    retry: (failureCount, error) => {
      // Don't retry on terminal errors
      if (error instanceof Error && error.message.includes("failed")) {
        return false;
      }
      return failureCount < 3;
    },
  });
}

// ── Dashboard ─────────────────────────────────────────────────────

export function useReviewDashboard() {
  return useQuery({
    queryKey: reviewKeys.dashboard(),
    queryFn: () => reviewService.getDashboard(),
    staleTime: 60_000, // 1 minute — dashboard refreshes less frequently
    gcTime: 5 * 60_000,
    refetchOnWindowFocus: true,
    retry: 2,
  });
}

// ── Findings ──────────────────────────────────────────────────────

export function useReviewFindings(
  reviewId: string | undefined,
  params?: { severity?: string; resolution?: string; page?: number; page_size?: number },
) {
  return useQuery({
    queryKey: [...reviewKeys.findings(reviewId!), params],
    queryFn: () => reviewService.listFindings(reviewId!, params),
    enabled: !!reviewId,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}

// ── Redlines ──────────────────────────────────────────────────────

export function useReviewRedlines(
  reviewId: string | undefined,
  status?: string,
) {
  return useQuery({
    queryKey: [...reviewKeys.redlines(reviewId!), { status }],
    queryFn: () => reviewService.listRedlines(reviewId!, status),
    enabled: !!reviewId,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
  });
}

// ── Comments ──────────────────────────────────────────────────────

export function useReviewComments(reviewId: string | undefined) {
  return useQuery({
    queryKey: reviewKeys.comments(reviewId!),
    queryFn: () => reviewService.listComments(reviewId!),
    enabled: !!reviewId,
    staleTime: 10_000,
    gcTime: 30_000,
  });
}

// ── History ───────────────────────────────────────────────────────

export function useReviewHistory(reviewId: string | undefined) {
  return useQuery({
    queryKey: reviewKeys.history(reviewId!),
    queryFn: () => reviewService.getHistory(reviewId!),
    enabled: !!reviewId,
    staleTime: 30_000,
    gcTime: 60_000,
  });
}

// ── Mutations ─────────────────────────────────────────────────────

/** Resolve a finding with optimistic cache update */
export function useResolveFinding(reviewId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      findingId,
      body,
    }: {
      findingId: string;
      body: FindingResolveRequest;
    }) => reviewService.resolveFinding(reviewId, findingId, body),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reviewKeys.findings(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: [...reviewKeys.all, "risk-breakdown", reviewId],
      });
    },
  });
}

/** Get risk breakdown for a review */
export function useRiskBreakdown(reviewId: string) {
  return useQuery({
    queryKey: [...reviewKeys.all, "risk-breakdown", reviewId] as const,
    queryFn: () => reviewService.getRiskBreakdown(reviewId),
    staleTime: 15_000,
    enabled: Boolean(reviewId),
  });
}

/** Get risk delta timeline for a review — shows every decision that changed risk */
export function useRiskDeltaTimeline(reviewId: string) {
  return useQuery({
    queryKey: [...reviewKeys.all, "risk-delta-timeline", reviewId] as const,
    queryFn: () => reviewService.getRiskDeltaTimeline(reviewId),
    staleTime: 30_000,
    enabled: Boolean(reviewId),
  });
}

/** Get risk waterfall chart data — shows original → decisions → remaining */
export function useRiskWaterfall(reviewId: string) {
  return useQuery({
    queryKey: [...reviewKeys.all, "risk-waterfall", reviewId] as const,
    queryFn: () => reviewService.getRiskWaterfall(reviewId),
    staleTime: 30_000,
    enabled: Boolean(reviewId),
  });
}

/** Get version impacts — risk changes grouped by document version */
export function useVersionImpacts(reviewId: string) {
  return useQuery({
    queryKey: [...reviewKeys.all, "version-impacts", reviewId] as const,
    queryFn: () => reviewService.getVersionImpacts(reviewId),
    staleTime: 30_000,
    enabled: Boolean(reviewId),
  });
}

/** Update a redline with optimistic cache update */
export function useUpdateRedline(reviewId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      redlineId,
      body,
    }: {
      redlineId: string;
      body: RedlineUpdateRequest;
    }) => reviewService.updateRedline(reviewId, redlineId, body),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reviewKeys.redlines(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: ["reviews", reviewId, "versions"],
      });
      queryClient.invalidateQueries({
        queryKey: [...reviewKeys.all, "risk-breakdown", reviewId],
      });
    },
  });
}

/** Add a comment with optimistic cache update */
export function useAddComment(reviewId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CommentCreateRequest) =>
      reviewService.addComment(reviewId, body),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reviewKeys.comments(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(reviewId),
      });
    },
  });
}

/** Assign a reviewer with status cache update */
export function useAssignReviewer(reviewId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: AssignRequest) =>
      reviewService.assign(reviewId, body),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.status(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.lists(),
      });
      queryClient.invalidateQueries({
        queryKey: ["reviews", "workload"],
      });
    },
  });
}

/** Escalate a review */
export function useEscalateReview(reviewId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: EscalateRequest) =>
      reviewService.escalate(reviewId, body),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.status(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.dashboard(),
      });
    },
  });
}

/** Approve or reject a review */
export function useApproveReview(reviewId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: ApproveRequest) =>
      reviewService.approve(reviewId, body),

    onSuccess: () => {
      // Invalidate all review data — status changes cascade
      queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.status(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.history(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.dashboard(),
      });
    },
  });
}

/** Update review status */
export function useUpdateReviewStatus(reviewId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      status,
      reason,
    }: {
      status: string;
      reason?: string;
    }) => reviewService.updateStatus(reviewId, status, reason),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.status(reviewId),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.history(reviewId),
      });
    },
  });
}

/** Trigger re-analysis with cache invalidation */
export function useReAnalyzeReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      reviewId,
      body,
    }: {
      reviewId: string;
      body?: Partial<ReAnalysisRequest>;
    }) => reviewService.reAnalyze(reviewId, body),

    onSuccess: (data) => {
      // Invalidate the review that was re-analyzed
      queryClient.invalidateQueries({
        queryKey: reviewKeys.detail(data.review_id),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.status(data.review_id),
      });
      // Invalidate findings and redlines — re-analysis creates new records with new IDs
      queryClient.invalidateQueries({
        queryKey: reviewKeys.findings(data.review_id),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.redlines(data.review_id),
      });
      // Invalidate risk-breakdown — risk scores and contributions recalculated
      queryClient.invalidateQueries({
        queryKey: [...reviewKeys.all, "risk-breakdown", data.review_id],
      });
      // Also invalidate uploads list (new analysis run created)
      queryClient.invalidateQueries({
        queryKey: ["uploads"],
      });
    },
  });
}

/** Soft delete a review */
export function useDeleteReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      reviewId,
      reason,
    }: {
      reviewId: string;
      reason?: string;
    }) => reviewService.softDelete(reviewId, { reason }),

    onSuccess: () => {
      // Invalidate all review lists
      queryClient.invalidateQueries({
        queryKey: reviewKeys.lists(),
      });
      queryClient.invalidateQueries({
        queryKey: reviewKeys.dashboard(),
      });
    },
  });
}

/** Generate a redline from a mitigation recommendation (closed-loop remediation) */
export function useGenerateMitigationRedline(reviewId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      mitigation_type: string;
      clause_category: string;
      finding_ids?: string[];
    }) => reviewService.generateMitigationRedline(reviewId, body),

    onSuccess: () => {
      // Invalidate redlines list so the new redline appears
      queryClient.invalidateQueries({
        queryKey: [...reviewKeys.detail(reviewId), "redlines"],
      });
      // Also invalidate risk breakdown since a new redline may change exposure
      queryClient.invalidateQueries({
        queryKey: [...reviewKeys.all, "risk-breakdown", reviewId],
      });
    },
  });
}

/**
 * Workspace hydration hook — fetches a complete review workspace in one request.
 *
 * Replaces 10+ parallel useQuery calls with a single hydration endpoint.
 * Provides:
 * - Review details, status, findings, risk breakdown, versions
 * - Workflow state, SLA info, reviewer workload
 * - Recent activity, unread notifications
 * - Recovery governance (last recovery action)
 * - Automatic cache invalidation on realtime events
 * - Stale-while-revalidate for instant navigation
 *
 * Usage:
 *   const { data, isLoading } = useWorkspace(reviewId);
 *
 *   // Access nested data:
 *   data.review          // ReviewDetail
 *   data.status          // ReviewStatusResponse
 *   data.findings        // FindingItem[]
 *   data.risk_breakdown  // RiskBreakdown | null
 *   data.versions        // DocumentVersionItem[]
 *   data.recent_activity // ActivityItem[]
 */

"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import { useEffect, useCallback } from "react";
import type { ReviewDetail, FindingItem } from "@/services/api/client";
import { getGlobalConnectionState } from "@/services/hooks/useAdaptivePolling";

// ── Types ─────────────────────────────────────────────────────────

export type ReviewStatusHydration = {
  review_id: string;
  upload_id: string;
  status: string;
  ingestion_state: string | null;
  ai_status: string | null;
  review_status: string | null;
  progress: number;
  current_step: string | null;
  error: string | null;
  error_code: string | null;
  can_retry: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type DocumentVersionItem = {
  version_id: string;
  review_id: string;
  version_number: number;
  label: string | null;
  status: string;
  source_document_id: string | null;
  storage_key: string | null;
  change_summary: string | null;
  accepted_redline_ids: string[] | null;
  file_size_bytes: number | null;
  mime_type: string | null;
  checksum_sha256: string | null;
  created_by: string;
  created_at: string;
};

export type ActivityItem = {
  activity_id: string;
  from_status: string;
  to_status: string;
  changed_by: string;
  reason: string | null;
  created_at: string;
};

export type RecoveryActionItem = {
  action_type: string;
  escalation_count: number;
  cooldown_until: string | null;
  success: boolean;
  message: string | null;
  created_at: string;
};

export type WorkspaceData = {
  review: ReviewDetail;
  status: ReviewStatusHydration;
  findings: FindingItem[];
  total_findings: number;
  risk_breakdown: Record<string, unknown> | null;
  risk_score: number | null;
  versions: DocumentVersionItem[];
  current_version: DocumentVersionItem | null;
  workflow_stage: string | null;
  escalation_count: number;
  sla_status: string;
  sla_deadline: string | null;
  assigned_to: string | null;
  reviewer_active_count: number;
  recent_activity: ActivityItem[];
  unread_notifications: number;
  last_recovery_action: RecoveryActionItem | null;
  hydrated_at: string;
  response_size_estimate_bytes: number;
};

// ── Query key factory ─────────────────────────────────────────────

export const workspaceKeys = {
  all: ["workspace"] as const,
  detail: (reviewId: string) => ["workspace", reviewId] as const,
};

// ── Hook ──────────────────────────────────────────────────────────

const STALE_TIME = 30_000; // 30 seconds — workspace data changes frequently
const CACHE_TIME = 5 * 60_000; // 5 minutes
const REFETCH_INTERVAL = 30_000; // Poll every 30s as fallback (until WebSocket is reliable)

type UseWorkspaceOptions = {
  /** Enable auto-refetching. Default: true */
  enabled?: boolean;
  /** Refetch interval in ms. Default: 30000. Set to 0 to disable polling. */
  refetchInterval?: number;
};

export function useWorkspace(
  reviewId: string | undefined,
  options: UseWorkspaceOptions = {},
) {
  const {
    enabled = true,
    refetchInterval = REFETCH_INTERVAL,
  } = options;

  const queryClient = useQueryClient();

  const query = useQuery<WorkspaceData>({
    queryKey: workspaceKeys.detail(reviewId!),
    queryFn: async () => {
      const response = await api.get(`/reviews/${reviewId}/workspace`);
      return response as WorkspaceData;
    },
    enabled: enabled && !!reviewId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    refetchInterval: (query) => {
      // Stop polling if WebSocket is connected — realtime events drive updates
      const connState = getGlobalConnectionState();
      if (connState === "connected") return false;

      // Don't refetch if data is fresh
      if (query.state.dataUpdatedAt > Date.now() - STALE_TIME) return false;

      // Adaptive polling based on connection state
      if (connState === "reconnecting") return 10_000; // Every 10s during reconnect
      if (refetchInterval === 0) return false;
      return refetchInterval;
    },
    // Use previous data while refetching to avoid layout shift
    placeholderData: (previousData) => previousData,
  });

  // ── Cache invalidation on realtime events ─────────────────────
  // Uses a debounce window to batch rapid invalidations from event bursts.
  // Tracks the last event sequence to reject stale/out-of-order events.
  const invalidate = useCallback(() => {
    if (reviewId) {
      debouncedInvalidate(queryClient, reviewId);
    }
  }, [reviewId, queryClient]);

  // Expose invalidate for external use (e.g., from WebSocket event handler)
  return {
    ...query,
    invalidate,
  };
}

// ── Debounced Invalidation ───────────────────────────────────────
//
// Prevents duplicate invalidations from rapid event sequences.
// When multiple events arrive in quick succession (e.g., a status
// change triggers both "review.status_changed" and "recovery.action_taken"),
// only one invalidation is executed within the debounce window.
//
// This prevents:
// - Multiple redundant network requests
// - UI flicker from repeated re-renders
// - Cache stampedes under event bursts

const INVALIDATION_DEBOUNCE_MS = 500; // 500ms debounce window

const invalidationTimers = new Map<string, ReturnType<typeof setTimeout>>();

function debouncedInvalidate(queryClient: ReturnType<typeof useQueryClient>, reviewId: string): void {
  const key = `workspace:${reviewId}`;

  // Clear any pending invalidation for this review
  const existing = invalidationTimers.get(key);
  if (existing) {
    clearTimeout(existing);
  }

  // Schedule a new invalidation
  invalidationTimers.set(
    key,
    setTimeout(() => {
      invalidationTimers.delete(key);
      queryClient.invalidateQueries({ queryKey: workspaceKeys.detail(reviewId) });
    }, INVALIDATION_DEBOUNCE_MS),
  );
}

// ── Stale Event Rejection ────────────────────────────────────────
//
// Tracks the last processed event sequence per review to reject
// stale or out-of-order events. This prevents:
//
// - Replayed events from overwriting newer state
// - Out-of-order WebSocket delivery (common under reconnect)
// - Duplicate events from competing workers
//
// Sequence tracking is per-review and persists across reconnects
// via the RealtimeClient's localStorage cursor.

const lastEventSequences = new Map<string, number>();

/**
 * Check if an event should be processed or rejected as stale.
 *
 * Returns true if the event is stale (should be ignored).
 * Returns false if the event is new (should be processed).
 */
export function isStaleEvent(reviewId: string, sequenceId?: number): boolean {
  if (!sequenceId) return false; // No sequence info — always process

  const lastSeq = lastEventSequences.get(reviewId) || 0;
  if (sequenceId <= lastSeq) {
    return true; // Stale — we've already processed a newer event
  }

  lastEventSequences.set(reviewId, sequenceId);
  return false;
}

/**
 * Clear sequence tracking for a review (e.g., on navigation away).
 */
export function clearEventSequence(reviewId: string): void {
  lastEventSequences.delete(reviewId);
}

// ── Prefetch ─────────────────────────────────────────────────────

/**
 * Prefetch a workspace into the cache (e.g., on hover or page transition).
 */
export function prefetchWorkspace(
  queryClient: ReturnType<typeof useQueryClient>,
  reviewId: string,
): Promise<void> {
  return queryClient.prefetchQuery({
    queryKey: workspaceKeys.detail(reviewId),
    queryFn: async () => {
      const response = await api.get(`/reviews/${reviewId}/workspace`);
      return response as WorkspaceData;
    },
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
  });
}

/**
 * Hook that subscribes to realtime events for a specific review
 * and invalidates the workspace cache when relevant events arrive.
 *
 * Features:
 * - Stale event rejection via sequence tracking
 * - Debounced invalidation to batch rapid events
 * - Automatic cleanup on unmount
 *
 * Usage:
 *   useWorkspaceRealtime(reviewId, realtimeClient);
 */
export function useWorkspaceRealtime(
  reviewId: string | undefined,
  client: {
    onEvent: (handler: (event: {
      type: string;
      data?: unknown;
      event_id?: string;
      sequence_id?: number;
    }) => void) => void;
    offEvent?: (handler: (...args: unknown[]) => void) => void;
  } | null,
) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!reviewId || !client) return;

    const handler = (event: {
      type: string;
      data?: unknown;
      event_id?: string;
      sequence_id?: number;
    }) => {
      // ── Stale event rejection ────────────────────────────────
      // Reject events that are older than what we've already processed.
      // This handles out-of-order delivery during WebSocket reconnects
      // where replay events may arrive interleaved with live events.
      if (isStaleEvent(reviewId, event.sequence_id)) {
        return;
      }

      // ── Filter relevant event types ──────────────────────────
      const matchesReview =
        event.type.startsWith("review.") ||
        event.type.startsWith("recovery.");

      if (!matchesReview) return;

      // ── Debounced invalidation ────────────────────────────────
      // Batch rapid event sequences into a single cache refresh.
      debouncedInvalidate(queryClient, reviewId);
    };

    client.onEvent(handler);

    return () => {
      // Cleanup sequence tracking on unmount
      clearEventSequence(reviewId);
    };
  }, [reviewId, client, queryClient]);
}

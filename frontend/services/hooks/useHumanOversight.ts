/**
 * Human Oversight query hooks — TanStack Query wrappers for human oversight API.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPendingExceptions,
  fetchPendingApprovals,
  fetchHumanOversightDashboard,
  decideApproval,
  reviewException,
  type ApprovalDecisionRequest,
  type ExceptionReviewRequest,
} from "@/services/api/humanOversight";

export const humanOversightKeys = {
  all: ["human-oversight"] as const,
  pendingExceptions: () => [...humanOversightKeys.all, "exceptions", "pending"] as const,
  pendingApprovals: () => [...humanOversightKeys.all, "approvals", "pending"] as const,
  dashboard: () => [...humanOversightKeys.all, "dashboard"] as const,
};

export function usePendingExceptions() {
  return useQuery({
    queryKey: humanOversightKeys.pendingExceptions(),
    queryFn: fetchPendingExceptions,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: humanOversightKeys.pendingApprovals(),
    queryFn: fetchPendingApprovals,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

export function useHumanOversightDashboard() {
  return useQuery({
    queryKey: humanOversightKeys.dashboard(),
    queryFn: fetchHumanOversightDashboard,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

// ── Mutation Hooks ──────────────────────────────────────────────────────

/**
 * Decide on an approval request (approve / reject / conditionally_approved).
 * Invalidates pending approvals and dashboard on success.
 */
export function useDecideApproval() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      approvalId,
      body,
    }: {
      approvalId: string;
      body: ApprovalDecisionRequest;
    }) => decideApproval(approvalId, body),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: humanOversightKeys.pendingApprovals() });
      queryClient.invalidateQueries({ queryKey: humanOversightKeys.dashboard() });
    },
  });
}

/**
 * Review a policy exception (approve / reject / conditionally_approved).
 * Invalidates pending exceptions and dashboard on success.
 */
export function useReviewException() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      exceptionId,
      body,
    }: {
      exceptionId: string;
      body: ExceptionReviewRequest;
    }) => reviewException(exceptionId, body),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: humanOversightKeys.pendingExceptions() });
      queryClient.invalidateQueries({ queryKey: humanOversightKeys.dashboard() });
    },
  });
}

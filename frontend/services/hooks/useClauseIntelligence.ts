/**
 * Clause Intelligence query hooks — TanStack Query wrappers for clause API.
 * Provides typed hooks for all 15 clause intelligence endpoints.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  clauseIntelligenceService,
  clauseIntelligenceKeys,
} from "@/services/api/clauseIntelligence";
import type {
  ClauseListParams,
  ClauseCreateRequest,
  ClauseUpdateRequest,
  AiReviewRequest,
  SimilarityRequest,
} from "@/services/api/clauseIntelligence";

// ── List / Paginated ──────────────────────────────────────────────

export function useClauses(params?: ClauseListParams) {
  return useQuery({
    queryKey: clauseIntelligenceKeys.list(params),
    queryFn: () => clauseIntelligenceService.listClauses(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

// ── Single Clause ─────────────────────────────────────────────────

export function useClause(id: string) {
  return useQuery({
    queryKey: clauseIntelligenceKeys.detail(id),
    queryFn: () => clauseIntelligenceService.getClause(id),
    enabled: !!id,
    staleTime: 60_000,
  });
}

// ── KPIs / Analytics ──────────────────────────────────────────────

export function useClauseKpis() {
  return useQuery({
    queryKey: clauseIntelligenceKeys.kpis(),
    queryFn: () => clauseIntelligenceService.getKpis(),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useBenchmarks() {
  return useQuery({
    queryKey: clauseIntelligenceKeys.benchmarks(),
    queryFn: () => clauseIntelligenceService.getBenchmarks(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function useDeviations() {
  return useQuery({
    queryKey: clauseIntelligenceKeys.deviations(),
    queryFn: () => clauseIntelligenceService.getDeviations(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

// ── AI Review / Similarity ────────────────────────────────────────

export function useAiReview() {
  return useMutation({
    mutationFn: (body: AiReviewRequest) =>
      clauseIntelligenceService.aiReview(body),
  });
}

export function useSimilarity() {
  return useMutation({
    mutationFn: (body: SimilarityRequest) =>
      clauseIntelligenceService.findSimilar(body),
  });
}

// ── Mutations (Create / Update / Delete) ──────────────────────────

export function useCreateClause() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ClauseCreateRequest) =>
      clauseIntelligenceService.createClause(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: clauseIntelligenceKeys.lists() });
    },
  });
}

export function useUpdateClause(id?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id?: string; body: ClauseUpdateRequest }) => {
      // Prefer the id passed at call time (so we can update any clause
      // from a list-level favorite toggle), falling back to the id captured
      // at hook creation time (e.g. the currently-open detail drawer).
      const targetId = vars.id ?? id;
      if (!targetId) {
        // Translate a missing id into a typed error so callers can show a
        // helpful message instead of letting the request hit a bare
        // /clauses/ endpoint and get back a 405 from the backend.
        const err = new Error("Cannot update clause: missing id");
        (err as Error & { status_code?: number }).status_code = 400;
        return Promise.reject(err);
      }
      return clauseIntelligenceService.updateClause(targetId, vars.body);
    },
    onSuccess: (_data, vars) => {
      const targetId = vars.id ?? id;
      if (targetId) {
        qc.invalidateQueries({ queryKey: clauseIntelligenceKeys.detail(targetId) });
      }
      qc.invalidateQueries({ queryKey: clauseIntelligenceKeys.lists() });
    },
  });
}

export function useDeleteClause() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      clauseIntelligenceService.deleteClause(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: clauseIntelligenceKeys.lists() });
    },
  });
}

// ── Fallbacks / Negotiations ──────────────────────────────────────

export function useFallbackVariants(id: string) {
  return useQuery({
    queryKey: clauseIntelligenceKeys.fallbacks(id),
    queryFn: () => clauseIntelligenceService.getFallbacks(id),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useNegotiationHistory(id: string) {
  return useQuery({
    queryKey: clauseIntelligenceKeys.negotiations(id),
    queryFn: () => clauseIntelligenceService.getNegotiations(id),
    enabled: !!id,
    staleTime: 60_000,
  });
}

// ── Trends / Market / Patterns ────────────────────────────────────

export function useUsageTrends() {
  return useQuery({
    queryKey: clauseIntelligenceKeys.usageTrends(),
    queryFn: () => clauseIntelligenceService.getUsageTrends(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function useMarketComparison() {
  return useQuery({
    queryKey: clauseIntelligenceKeys.marketComparison(),
    queryFn: () => clauseIntelligenceService.getMarketComparison(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function useRejectionPatterns() {
  return useQuery({
    queryKey: clauseIntelligenceKeys.rejectionPatterns(),
    queryFn: () => clauseIntelligenceService.getRejectionPatterns(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

/**
 * Search query hooks — TanStack Query wrappers for the search API.
 *
 * Provides hooks for hybrid search, findings search, clause search,
 * popular queries, zero-result queries, and click tracking.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";

// ── Query Key Factory ─────────────────────────────────────────────

export const searchKeys = {
  all: ["search"] as const,
  search: (params: Record<string, unknown>) =>
    [...searchKeys.all, "search", params] as const,
  findings: (params: Record<string, unknown>) =>
    [...searchKeys.all, "findings", params] as const,
  clauses: (params: Record<string, unknown>) =>
    [...searchKeys.all, "clauses", params] as const,
  popular: () => [...searchKeys.all, "popular"] as const,
  zeroResult: () => [...searchKeys.all, "zero-result"] as const,
};

// ── Types ─────────────────────────────────────────────────────────

export interface SearchResultItem {
  chunk_id: string;
  entity_type?: string;
  entity_id?: string | null;
  review_id?: string | null;
  contract_id?: string | null;
  contract_name?: string | null;
  contract_number?: string | null;
  upload_id?: string | null;
  page_numbers: number[];
  section_heading?: string | null;
  clause_type?: string | null;
  snippet: string;
  score: number;
  strategy: string;
  token_count: number;
  status?: string | null;
  owner?: string | null;
  due_date?: string | null;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total: number;
  page: number;
  page_size: number;
  query: string;
  strategy: string;
  latency_ms: number;
}

export interface SearchParams {
  q: string;
  strategy?: "hybrid" | "vector" | "keyword";
  clause_type?: string;
  contract_id?: string;
  entity_types?: string;
  page?: number;
  page_size?: number;
}

// ── Search Hook ───────────────────────────────────────────────────

export function useSearch(params: SearchParams | null) {
  return useQuery({
    queryKey: searchKeys.search((params ?? {}) as Record<string, unknown>),
    queryFn: async () => {
      if (!params || !params.q) {
        return { results: [], total: 0, page: 1, page_size: 20, query: "", strategy: "hybrid", latency_ms: 0 };
      }
      const queryParams = new URLSearchParams();
      queryParams.set("q", params.q);
      if (params.strategy) queryParams.set("strategy", params.strategy);
      if (params.clause_type) queryParams.set("clause_type", params.clause_type);
      if (params.contract_id) queryParams.set("contract_id", params.contract_id);
      if (params.entity_types) queryParams.set("entity_types", params.entity_types);
      if (params.page) queryParams.set("page", String(params.page));
      if (params.page_size) queryParams.set("page_size", String(params.page_size));
      return api.get<SearchResponse>(`/search?${queryParams.toString()}`);
    },
    enabled: !!params && !!params.q,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 2,
  });
}

// ── Findings Search Hook ──────────────────────────────────────────

export interface FindingsSearchParams {
  q: string;
  severity?: string;
  clause_type?: string;
  resolution?: string;
  review_id?: string;
  page?: number;
  page_size?: number;
}

export function useSearchFindings(params: FindingsSearchParams | null) {
  return useQuery({
    queryKey: searchKeys.findings((params ?? {}) as Record<string, unknown>),
    queryFn: async () => {
      const queryParams = new URLSearchParams();
      queryParams.set("q", params?.q ?? "");
      if (params?.severity) queryParams.set("severity", params.severity);
      if (params?.clause_type) queryParams.set("clause_type", params.clause_type);
      if (params?.resolution) queryParams.set("resolution", params.resolution);
      if (params?.review_id) queryParams.set("review_id", params.review_id);
      if (params?.page) queryParams.set("page", String(params.page));
      if (params?.page_size) queryParams.set("page_size", String(params.page_size));
      return api.get<{ results: unknown[]; total: number }>(`/search/findings?${queryParams.toString()}`);
    },
    enabled: !!params && !!params.q,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

// ── Clause Search Hook ────────────────────────────────────────────

export interface ClauseSearchParams {
  q: string;
  clause_type?: string;
  contract_id?: string;
  page?: number;
  page_size?: number;
}

export function useSearchClauses(params: ClauseSearchParams | null) {
  return useQuery({
    queryKey: searchKeys.clauses((params ?? {}) as Record<string, unknown>),
    queryFn: async () => {
      const queryParams = new URLSearchParams();
      queryParams.set("q", params?.q ?? "");
      if (params?.clause_type) queryParams.set("clause_type", params.clause_type);
      if (params?.contract_id) queryParams.set("contract_id", params.contract_id);
      if (params?.page) queryParams.set("page", String(params.page));
      if (params?.page_size) queryParams.set("page_size", String(params.page_size));
      return api.get<{ results: unknown[]; total: number }>(`/search/clauses?${queryParams.toString()}`);
    },
    enabled: !!params && !!params.q,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

// ── Search Pulse (portfolio intelligence on page load) ──────────

export interface SearchPulseResponse {
  total_chunks: number;
  total_contracts: number;
  total_findings: number;
  avg_risk_score: number | null;
  queries_today: number;
  popular_queries: { query: string; frequency: number }[];
  suggestions: {
    query: string;
    description: string;
    category: string;
    result_count: number;
    severity: string;
  }[];
  insights: {
    type: string;
    title: string;
    description: string;
    severity: string;
    confidence: number;
    impact: string;
    entities: string[];
    suggested_query: string | null;
    finding_count: number;
  }[];
}

export function useSearchPulse() {
  return useQuery({
    queryKey: [...searchKeys.all, "pulse"],
    queryFn: () => api.get<SearchPulseResponse>("/search/pulse"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 2,
  });
}

// ── Popular Queries ───────────────────────────────────────────────

export function usePopularQueries() {
  return useQuery({
    queryKey: searchKeys.popular(),
    queryFn: () => api.get<{ queries: { query: string; count: number }[] }>("/search/popular"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

// ── Zero-Result Queries ───────────────────────────────────────────

export function useZeroResultQueries() {
  return useQuery({
    queryKey: searchKeys.zeroResult(),
    queryFn: () => api.get<{ queries: { query: string; count: number }[] }>("/search/zero-results"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

// ── Click Tracking Mutation ───────────────────────────────────────

export function useTrackSearchClick() {
  return useMutation({
    mutationFn: (body: {
      query: string;
      result_position: number;
      entity_type: string;
      entity_id: string;
      chunk_id?: string;
      score?: number;
    }) => api.post("/search/click", body),
  });
}

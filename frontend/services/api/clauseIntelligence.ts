/**
 * Clause Intelligence API service — clause library, AI review, benchmarks & analytics.
 *
 * Maps to backend endpoints under `/api/v1/clauses/`.
 *
 * Provides typed API client methods for:
 * - Clause CRUD (list, get, create, update, delete)
 * - AI review & similarity search
 * - KPIs, benchmarks, deviations, usage trends, market comparison, rejection patterns
 * - Fallback variants & negotiation history
 *
 * Usage:
 *   import { clauseIntelligenceService } from '@/services/api/clauseIntelligence';
 *   const clauses = await clauseIntelligenceService.listClauses({ page: 1, pageSize: 20 });
 *   const kpis = await clauseIntelligenceService.getKpis();
 *   const review = await clauseIntelligenceService.aiReview({ clause_text: '...', category: '...' });
 */

"use client";

import { api } from "@/services/api/client";

// ── Types ─────────────────────────────────────────────────────────

export type ClauseCategory =
  | "indemnification"
  | "limitation_of_liability"
  | "confidentiality"
  | "data_privacy"
  | "intellectual_property"
  | "termination"
  | "governing_law"
  | "dispute_resolution"
  | "force_majeure"
  | "payment_terms"
  | "warranty"
  | "insurance"
  | "compliance"
  | "audit_rights"
  | "assignment"
  | "non_compete"
  | "non_solicit"
  | "sla"
  | "escrow"
  | "general";

export type ApprovalStatus = "draft" | "approved" | "pending_review" | "deprecated";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type SortOrder = "asc" | "desc";

// ── Request / Response DTOs ───────────────────────────────────────

export interface ClauseCreateRequest {
  name: string;
  category: string;
  clause_type?: string;
  text: string;
  jurisdiction?: string;
  contract_types?: string[];
  risk_score?: number;
  owner?: string;
  tags?: string[];
  governance_notes?: string;
}

export interface ClauseUpdateRequest {
  name?: string;
  category?: string;
  clause_type?: string;
  text?: string;
  jurisdiction?: string;
  contract_types?: string[];
  risk_score?: number;
  ai_confidence?: number;
  ai_explanation?: string;
  negotiation_strength?: number;
  negotiation_guidance?: string;
  approval_status?: string;
  owner?: string;
  is_favorite?: boolean;
  tags?: string[];
  governance_notes?: string;
}

export interface ClauseResponse {
  id: string;
  name: string;
  category: string;
  clause_type: string | null;
  text: string;
  jurisdiction: string | null;
  contract_types: string[];
  risk_score: number | null;
  risk_level: string | null;
  ai_confidence: number | null;
  ai_explanation: string | null;
  negotiation_strength: number | null;
  negotiation_guidance: string | null;
  benchmark_percentile: number | null;
  usage_frequency: number;
  approval_status: string;
  owner: string | null;
  version: number;
  is_favorite: boolean;
  tags: string[];
  deviation_frequency: number;
  market_percentile: number | null;
  playbook_linkage: string | null;
  governance_notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ClauseListParams {
  page?: number;
  page_size?: number;
  category?: string;
  search?: string;
  approval_status?: string;
  risk_level?: string;
  sort_by?: string;
  sort_order?: SortOrder;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface PaginatedClauses {
  data: ClauseResponse[];
  pagination: PaginationMeta;
}

export interface FallbackVariantResponse {
  id: string;
  label: string;
  text: string;
  risk_score: number | null;
  negotiation_strength: number | null;
  usage_rate: number | null;
  is_preferred: boolean;
  jurisdiction: string | null;
}

export interface BenchmarkResponse {
  category: string;
  market_median: number;
  market_p25: number | null;
  market_p75: number | null;
  sample_size: number;
  avg_risk_score: number | null;
  acceptance_rate: number | null;
  deviation_rate: number | null;
}

export interface NegotiationHistoryResponse {
  id: string;
  clause_id: string;
  counterparty: string | null;
  original_text: string;
  negotiated_text: string | null;
  outcome: string | null;
  risk_delta: number | null;
  strategy_used: string | null;
  success: boolean | null;
  created_by: string | null;
  created_at: string | null;
}

export interface AiReviewRequest {
  clause_text: string;
  category: string;
  jurisdiction?: string;
  contract_type?: string;
}

export interface AiReviewResponse {
  risk_score: number;
  risk_level: string;
  confidence: number;
  explanation: string;
  negotiation_strength: number;
  negotiation_guidance: string;
  compliance_warnings: string[];
  suggested_fallback: string | null;
  escalation_triggers: string[];
}

export interface SimilarityRequest {
  clause_text: string;
  category?: string;
  limit?: number;
}

export interface SimilarityResult {
  clause_id: string;
  name: string;
  similarity: number;
  text: string;
  category: string;
  risk_score: number | null;
}

export interface DeviationResponse {
  clause_id: string;
  name: string;
  category: string;
  deviation_score: number;
  market_median: number;
  your_score: number;
  risk_impact: string;
  recommendation: string;
}

export interface UsageTrendResponse {
  date: string;
  count: number;
  category: string | null;
}

export interface MarketComparisonResponse {
  category: string;
  your_percentile: number;
  market_median: number;
  market_p25: number;
  market_p75: number;
  sample_size: number;
}

export interface RejectionPatternResponse {
  category: string;
  rejection_rate: number;
  common_reasons: string[];
  recommendation: string;
}

export interface ClauseKpiResponse {
  total_clauses: number;
  approved_count: number;
  pending_review: number;
  deprecated_count: number;
  avg_risk_score: number;
  avg_ai_confidence: number;
  total_fallbacks: number;
  total_playbooks: number;
}

// ── Query Key Factory ─────────────────────────────────────────────

export const clauseIntelligenceKeys = {
  all: ["clause-intelligence"] as const,
  lists: () => [...clauseIntelligenceKeys.all, "list"] as const,
  list: (params?: ClauseListParams) => [...clauseIntelligenceKeys.lists(), params] as const,
  details: () => [...clauseIntelligenceKeys.all, "detail"] as const,
  detail: (id: string) => [...clauseIntelligenceKeys.details(), id] as const,
  kpis: () => [...clauseIntelligenceKeys.all, "kpis"] as const,
  benchmarks: () => [...clauseIntelligenceKeys.all, "benchmarks"] as const,
  deviations: () => [...clauseIntelligenceKeys.all, "deviations"] as const,
  fallbacks: (id: string) => [...clauseIntelligenceKeys.all, "fallbacks", id] as const,
  negotiations: (id: string) => [...clauseIntelligenceKeys.all, "negotiations", id] as const,
  usageTrends: () => [...clauseIntelligenceKeys.all, "usage-trends"] as const,
  marketComparison: () => [...clauseIntelligenceKeys.all, "market-comparison"] as const,
  rejectionPatterns: () => [...clauseIntelligenceKeys.all, "rejection-patterns"] as const,
};

// ── Service ───────────────────────────────────────────────────────

const CLAUSES_BASE = "/clauses";

export const clauseIntelligenceService = {
  // ── List / Paginated ──────────────────────────────────────────

  /** List clauses with pagination and filtering */
  listClauses: (params?: ClauseListParams) =>
    api.get<PaginatedClauses>(`${CLAUSES_BASE}/`, params as Record<string, unknown>),

  // ── KPIs / Analytics ──────────────────────────────────────────

  /** Get clause KPIs (totals, averages, counts) */
  getKpis: () =>
    api.get<ClauseKpiResponse>(`${CLAUSES_BASE}/kpis`),

  /** Get benchmark data per category */
  getBenchmarks: () =>
    api.get<{ data: BenchmarkResponse[] }>(`${CLAUSES_BASE}/benchmarks`),

  /** Get deviation data for clauses */
  getDeviations: () =>
    api.get<{ data: DeviationResponse[] }>(`${CLAUSES_BASE}/deviations`),

  // ── AI Review / Similarity ────────────────────────────────────

  /** Run AI review on a clause text */
  aiReview: (body: AiReviewRequest) =>
    api.post<AiReviewResponse>(`${CLAUSES_BASE}/ai-review`, body),

  /** Find clauses similar to a given text */
  findSimilar: (body: SimilarityRequest) =>
    api.post<{ data: SimilarityResult[] }>(`${CLAUSES_BASE}/similarity`, body),

  // ── CRUD ──────────────────────────────────────────────────────

  /** Get a single clause by ID */
  getClause: (id: string) =>
    api.get<ClauseResponse>(`${CLAUSES_BASE}/${id}`),

  /** Create a new clause */
  createClause: (body: ClauseCreateRequest) =>
    api.post<ClauseResponse>(`${CLAUSES_BASE}/`, body),

  /** Update an existing clause */
  updateClause: (id: string, body: ClauseUpdateRequest) =>
    api.put<ClauseResponse>(`${CLAUSES_BASE}/${id}`, body),

  /** Delete a clause */
  deleteClause: (id: string) =>
    api.delete<void>(`${CLAUSES_BASE}/${id}`),

  // ── Fallbacks / Negotiations ──────────────────────────────────

  /** Get fallback variants for a clause */
  getFallbacks: (id: string) =>
    api.get<FallbackVariantResponse[]>(`${CLAUSES_BASE}/${id}/fallbacks`),

  /** Get negotiation history for a clause */
  getNegotiations: (id: string) =>
    api.get<{ data: NegotiationHistoryResponse[] }>(`${CLAUSES_BASE}/${id}/negotiations`),

  // ── Trends / Market / Patterns ────────────────────────────────

  /** Get usage trends over time */
  getUsageTrends: () =>
    api.get<{ data: UsageTrendResponse[] }>(`${CLAUSES_BASE}/usage-trends`),

  /** Get market comparison data */
  getMarketComparison: () =>
    api.get<{ data: MarketComparisonResponse[] }>(`${CLAUSES_BASE}/market-comparison`),

  /** Get rejection patterns by category */
  getRejectionPatterns: () =>
    api.get<{ data: RejectionPatternResponse[] }>(`${CLAUSES_BASE}/rejection-patterns`),
};

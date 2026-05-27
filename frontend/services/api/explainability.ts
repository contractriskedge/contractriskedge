/**
 * Explainability API service — AI evidence chains and confidence scoring.
 *
 * Sprint 7 Priority 2.
 *
 * Provides typed API client methods for:
 * - Evidence chain retrieval per finding
 * - Confidence scoring
 * - Precedent linkage
 * - Regulation citation mapping
 * - Alternative recommendations
 *
 * Usage:
 *   import { explainabilityService } from '@/services/api/explainability';
 *   const evidence = await explainabilityService.getEvidenceChain(reviewId, findingId);
 */

"use client";

import { api } from "@/services/api/client";

// ── Types ─────────────────────────────────────────────────────────

export type EvidenceLinkType =
  | "clause"
  | "regulation"
  | "precedent"
  | "mitigation"
  | "playbook"
  | "benchmark"
  | "custom";

export type ConfidenceBasis =
  | "exact_match"
  | "semantic_match"
  | "llm_reasoning"
  | "rule_based"
  | "statistical"
  | "human_review"
  | "regulatory_requirement";

export interface EvidenceLink {
  link_id: string;
  type: EvidenceLinkType;
  source: string;
  source_label: string;
  excerpt: string;
  relevance: number; // 0-1
  contribution: number; // impact on final score (0-1)
  confidence: number; // 0-1
  basis: ConfidenceBasis;
  source_url?: string;
  supporting_data?: Record<string, unknown>;
}

export interface AlternativeRecommendation {
  recommendation_id: string;
  title: string;
  description: string;
  impact: string;
  risk_reduction_estimate: number; // percentage points
  confidence: number; // 0-1
  effort: "low" | "medium" | "high";
  precedent_count: number;
  sample_clause?: string;
}

export interface EvidenceChain {
  finding_id: string;
  finding_title: string;
  score: number; // 0-100
  confidence: number; // 0-1
  chain: EvidenceLink[];
  alternatives: AlternativeRecommendation[];
  benchmark_percentile: number | null;
  regulation_citations: RegulationCitation[];
  evaluated_at: string;
}

export interface RegulationCitation {
  regulation_id: string;
  name: string;
  jurisdiction: string;
  category: string;
  relevance: number; // 0-1
  excerpt: string;
  compliance_required: boolean;
}

export interface PrecedentLink {
  precedent_id: string;
  contract_id: string;
  contract_name: string;
  clause_type: string;
  resolution: string;
  outcome: string;
  similarity_score: number;
  linked_at: string;
}

export interface ConfidenceBreakdown {
  overall: number; // 0-1
  dimensions: {
    data_quality: number;
    model_confidence: number;
    rule_match: number;
    human_validation: number;
    temporal_relevance: number;
  };
  basis: ConfidenceBasis;
  explanation: string;
}

// ── Query Key Factory ─────────────────────────────────────────────

export const explainabilityKeys = {
  all: ["explainability"] as const,
  evidence: (reviewId: string, findingId: string) =>
    [...explainabilityKeys.all, "evidence", reviewId, findingId] as const,
  precedents: (reviewId: string, findingId: string) =>
    [...explainabilityKeys.all, "precedents", reviewId, findingId] as const,
  regulations: (reviewId: string) =>
    [...explainabilityKeys.all, "regulations", reviewId] as const,
  confidence: (reviewId: string, findingId: string) =>
    [...explainabilityKeys.all, "confidence", reviewId, findingId] as const,
};

// ── Service ───────────────────────────────────────────────────────

export const explainabilityService = {
  /** Get the full evidence chain for a specific finding */
  getEvidenceChain: (reviewId: string, findingId: string) =>
    api.get<EvidenceChain>(`/reviews/${reviewId}/findings/${findingId}/evidence`),

  /** Get precedent contracts with similar findings */
  getPrecedents: (reviewId: string, findingId: string, options?: { limit?: number; min_similarity?: number }) =>
    api.get<{ data: PrecedentLink[] }>(`/reviews/${reviewId}/findings/${findingId}/precedents`, options as Record<string, unknown>),

  /** Get regulation citations relevant to a review */
  getRegulationCitations: (reviewId: string) =>
    api.get<{ data: RegulationCitation[] }>(`/reviews/${reviewId}/regulations`),

  /** Get confidence breakdown for a finding */
  getConfidenceBreakdown: (reviewId: string, findingId: string) =>
    api.get<ConfidenceBreakdown>(`/reviews/${reviewId}/findings/${findingId}/confidence`),

  /** Get alternative recommendations for a finding */
  getAlternatives: (reviewId: string, findingId: string) =>
    api.get<{ data: AlternativeRecommendation[] }>(`/reviews/${reviewId}/findings/${findingId}/alternatives`),
};

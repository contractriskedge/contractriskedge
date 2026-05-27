/**
 * Clause Intelligence API service — clause relationship graph and knowledge base.
 *
 * Sprint 7 Priority 3.
 *
 * Provides typed API client methods for:
 * - Clause relationship graph (nodes, edges)
 * - Alternative and fallback clause recommendations
 * - Vendor clause profiles and behavior patterns
 * - Negotiation history per clause type
 * - Clause co-occurrence analysis
 *
 * Usage:
 *   import { clauseIntelligenceService } from '@/services/api/clauseIntelligence';
 *   const graph = await clauseIntelligenceService.getClauseGraph(reviewId);
 *   const alternatives = await clauseIntelligenceService.getAlternatives(clauseId);
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

export type ClauseRelationshipType =
  | "alternative"
  | "fallback"
  | "conflicts_with"
  | "depends_on"
  | "co_occurs_with"
  | "strengthens"
  | "weakens"
  | "supersedes";

export type ClauseStatus = "approved" | "preferred" | "fallback" | "forbidden" | "conditional";

export interface ClauseNode {
  clause_id: string;
  review_id?: string;
  category: ClauseCategory;
  clause_type: string;
  text: string;
  summary: string;
  risk_score: number | null;
  status: ClauseStatus;
  source: "extracted" | "standard" | "negotiated" | "benchmark";
  version: number;
  metadata: Record<string, unknown>;
}

export interface ClauseEdge {
  edge_id: string;
  source_clause_id: string;
  target_clause_id: string;
  relationship: ClauseRelationshipType;
  strength: number; // 0-1
  context: string | null;
  evidence: string | null;
}

export interface ClauseGraph {
  nodes: ClauseNode[];
  edges: ClauseEdge[];
  metadata: {
    total_clauses: number;
    total_relationships: number;
    categories_represented: ClauseCategory[];
    generated_at: string;
  };
}

export interface ClauseVariant {
  variant_id: string;
  clause_id: string;
  category: ClauseCategory;
  text: string;
  status: ClauseStatus;
  acceptance_rate: number;
  usage_count: number;
  source: string;
}

export interface NegotiationEntry {
  negotiation_id: string;
  contract_id: string;
  contract_name: string;
  clause_category: ClauseCategory;
  original_text: string;
  negotiated_text: string;
  outcome: "accepted" | "rejected" | "modified" | "removed";
  risk_delta: number;
  negotiated_by: string;
  negotiated_at: string;
  notes: string | null;
}

export interface VendorClauseProfile {
  vendor_id: string;
  vendor_name: string;
  total_contracts: number;
  clause_profiles: {
    category: ClauseCategory;
    acceptance_rate: number;
    common_alternatives: ClauseVariant[];
    average_risk_score: number;
    negotiation_count: number;
  }[];
  last_updated: string;
}

export interface ClauseCoOccurrence {
  category_a: ClauseCategory;
  category_b: ClauseCategory;
  frequency: number;
  strength: number; // 0-1 (lift)
  sample_contracts: string[];
}

// ── Query Key Factory ─────────────────────────────────────────────

export const clauseIntelligenceKeys = {
  all: ["clause-intelligence"] as const,
  graph: (reviewId: string) => [...clauseIntelligenceKeys.all, "graph", reviewId] as const,
  alternatives: (clauseId: string) => [...clauseIntelligenceKeys.all, "alternatives", clauseId] as const,
  vendorProfile: (vendorId: string) => [...clauseIntelligenceKeys.all, "vendor", vendorId] as const,
  negotiationHistory: (clauseCategory: ClauseCategory) =>
    [...clauseIntelligenceKeys.all, "negotiations", clauseCategory] as const,
  coOccurrences: () => [...clauseIntelligenceKeys.all, "co-occurrences"] as const,
};

// ── Service ───────────────────────────────────────────────────────

export const clauseIntelligenceService = {
  /** Get the clause relationship graph for a review */
  getClauseGraph: (reviewId: string) =>
    api.get<ClauseGraph>(`/reviews/${reviewId}/clause-graph`),

  /** Get alternative clauses for a specific clause */
  getAlternatives: (clauseId: string, options?: { limit?: number; min_strength?: number }) =>
    api.get<{ data: ClauseVariant[] }>(`/clauses/${clauseId}/alternatives`, options as Record<string, unknown>),

  /** Get fallback chain for a clause category */
  getFallbackChain: (category: ClauseCategory) =>
    api.get<{ data: ClauseVariant[] }>(`/clauses/fallback-chain/${category}`),

  /** Get vendor clause profile */
  getVendorProfile: (vendorId: string) =>
    api.get<VendorClauseProfile>(`/vendors/${vendorId}/clause-profile`),

  /** Get negotiation history for a clause category */
  getNegotiationHistory: (category: ClauseCategory, options?: { limit?: number; vendor_id?: string }) =>
    api.get<{ data: NegotiationEntry[] }>(`/clauses/negotiations/${category}`, options as Record<string, unknown>),

  /** Get clause co-occurrence patterns */
  getCoOccurrences: (options?: { min_frequency?: number; category?: ClauseCategory }) =>
    api.get<{ data: ClauseCoOccurrence[] }>("/clauses/co-occurrences", options as Record<string, unknown>),
};

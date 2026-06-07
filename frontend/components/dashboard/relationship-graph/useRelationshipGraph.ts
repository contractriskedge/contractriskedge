/**
 * useRelationshipGraph — React Query hook for the Relationships Graph API.
 *
 * Fetches entity relationship graph data from GET /api/v1/relationships/graph.
 * Supports review_id, upload_id, and depth parameters.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { RelationshipGraphResponse } from "@/components/dashboard/relationship-graph/types";

const RELATIONSHIPS_BASE = "/relationships";

export const relationshipKeys = {
  all: ["relationships"] as const,
  graph: (params: { review_id?: string; upload_id?: string; depth?: number }) =>
    [...relationshipKeys.all, "graph", params] as const,
};

interface FetchGraphParams {
  review_id?: string;
  upload_id?: string;
  depth?: number;
}

async function fetchRelationshipGraph(params: FetchGraphParams): Promise<RelationshipGraphResponse> {
  const searchParams = new URLSearchParams();
  if (params.review_id) searchParams.set("review_id", params.review_id);
  if (params.upload_id) searchParams.set("upload_id", params.upload_id);
  if (params.depth) searchParams.set("depth", String(params.depth));
  const qs = searchParams.toString();
  return api.get<RelationshipGraphResponse>(`${RELATIONSHIPS_BASE}/graph${qs ? `?${qs}` : ""}`);
}

export function useRelationshipGraph(params: FetchGraphParams) {
  const hasParams = !!(params.review_id || params.upload_id);

  return useQuery({
    queryKey: relationshipKeys.graph(params),
    queryFn: () => fetchRelationshipGraph(params),
    staleTime: 5 * 60_000,  // 5 min — matches backend cache TTL
    gcTime: 10 * 60_000,     // 10 min cache
    enabled: hasParams,
    retry: 2,
  });
}

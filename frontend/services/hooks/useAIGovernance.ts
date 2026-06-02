/**
 * React Query hooks for AI Governance.
 *
 * Provides live data hooks for:
 * - AI Quality Dashboard (quality score trend, regressions, usage stats)
 * - Prompt Registry (deployment history, version listing)
 */

import { useQuery } from "@tanstack/react-query";
import {
  fetchAIQualityDashboard,
  fetchPrompts,
  aiGovernanceKeys,
  type AIQualityDashboard,
  type PromptSummary,
} from "@/services/api/aiGovernance";

export { aiGovernanceKeys };

/**
 * Hook: AI Quality Dashboard data.
 *
 * Returns the quality score trend, recent regressions, model usage stats,
 * and prompt health metrics from GET /api/v1/ai-governance/quality-dashboard.
 */
export function useAIQualityDashboard() {
  return useQuery<AIQualityDashboard>({
    queryKey: aiGovernanceKeys.quality(),
    queryFn: fetchAIQualityDashboard,
    staleTime: 60_000,
    retry: 2,
  });
}

/**
 * Hook: Prompt template registry.
 *
 * Returns all prompt templates with their latest version info
 * from GET /api/v1/ai-governance/prompts.
 */
export function usePrompts() {
  return useQuery<PromptSummary[]>({
    queryKey: aiGovernanceKeys.prompts(),
    queryFn: fetchPrompts,
    staleTime: 30_000,
    retry: 2,
  });
}

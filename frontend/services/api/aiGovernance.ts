/**
 * AI Governance API client — prompt registry, evaluation, quality dashboard.
 *
 * Endpoint prefix: /api/v1/ai-governance
 */

import { api } from "@/services/api/client";

export interface PromptSummary {
  prompt_key: string;
  name: string;
  description?: string;
  active_version: number;
  state: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface ModelUsageSummary {
  model: string;
  provider: string;
  inferences_24h: number;
  avg_latency_ms: number;
  total_tokens: number;
  cost_usd: number;
  error_rate: number;
}

export interface AIQualityDashboard {
  total_prompts: number;
  active_prompts: number;
  total_evaluation_datasets: number;
  total_test_cases: number;
  last_regression_pass_rate: number | null;
  regressions_found_last_run: number;
  avg_calibration_error: number | null;
  total_inferences_24h: number;
  inference_success_rate_24h: number;
  avg_latency_ms_24h: number;
  total_cost_24h: number;
  model_usage: ModelUsageSummary[];
  recent_errors: any[];
}

export const aiGovernanceKeys = {
  all: ["ai-governance"] as const,
  quality: () => [...aiGovernanceKeys.all, "quality-dashboard"] as const,
  prompts: () => [...aiGovernanceKeys.all, "prompts"] as const,
};

export async function fetchAIQualityDashboard(): Promise<AIQualityDashboard> {
  return api.get<AIQualityDashboard>("/ai-governance/quality-dashboard");
}

export async function fetchPrompts(): Promise<PromptSummary[]> {
  return api.get<PromptSummary[]>("/ai-governance/prompts");
}

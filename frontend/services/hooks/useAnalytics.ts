/**
 * Analytics query hooks — TanStack Query wrappers for the analytics API.
 *
 * Provides hooks for error analytics, stuck workflows, system health,
 * metrics summary, and query performance.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api/client";

// ── Query Key Factory ─────────────────────────────────────────────

export const analyticsKeys = {
  all: ["analytics"] as const,
  errors: (periodHours?: number) =>
    [...analyticsKeys.all, "errors", { periodHours }] as const,
  stuckWorkflows: () => [...analyticsKeys.all, "stuck-workflows"] as const,
  health: () => [...analyticsKeys.all, "health"] as const,
  metrics: () => [...analyticsKeys.all, "metrics"] as const,
  queryPerformance: () => [...analyticsKeys.all, "query-performance"] as const,
  uploadTrend: (days?: number) => [...analyticsKeys.all, "upload-trend", { days }] as const,
  riskDistribution: () => [...analyticsKeys.all, "risk-distribution"] as const,
  findingsByClause: () => [...analyticsKeys.all, "findings-by-clause"] as const,
  aiCostTrend: (days?: number) => [...analyticsKeys.all, "ai-cost-trend", { days }] as const,
  reviewAging: () => [...analyticsKeys.all, "review-aging"] as const,
  executiveSummary: () => [...analyticsKeys.all, "executive-summary"] as const,
};

// ── Types ─────────────────────────────────────────────────────────

export interface SystemHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  active_uploads: number;
  active_ai_runs: number;
  pending_reviews: number;
  recent_errors_24h: number;
  sla_breaches: number;
  upload_success_rate: number;
  ai_success_rate: number;
}

export interface MetricsSummaryResponse {
  total_uploads_24h: number;
  total_reviews_24h: number;
  total_findings_24h: number;
  upload_success_rate: number;
  ai_success_rate: number;
  avg_upload_latency_ms: number;
  avg_ai_latency_ms: number;
  total_tokens_used: number;
  total_cost_usd: number;
}

export interface ErrorAnalyticsResponse {
  total_failures: number;
  by_type: Record<string, number>;
  by_domain: Record<string, number>;
  retryable_count: number;
  non_retryable_count: number;
  top_failing_uploads: Array<{ upload_id: string; filename: string; error: string; count: number }>;
}

export interface StuckWorkflowsResponse {
  stuck_uploads: number;
  stuck_ai_runs: number;
  stuck_reviews: number;
  items: Array<{ id: string; type: string; state: string; stuck_minutes: number }>;
}

// ── Hooks ─────────────────────────────────────────────────────────

export function useSystemHealth() {
  return useQuery({
    queryKey: analyticsKeys.health(),
    queryFn: () => api.get<SystemHealthResponse>("/analytics/health"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 2,
  });
}

export function useMetricsSummary() {
  return useQuery({
    queryKey: analyticsKeys.metrics(),
    queryFn: () => api.get<MetricsSummaryResponse>("/analytics/metrics"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 2,
  });
}

export function useErrorAnalytics(periodHours?: number) {
  return useQuery({
    queryKey: analyticsKeys.errors(periodHours ?? 24),
    queryFn: () => {
      const params = periodHours ? `?period_hours=${periodHours}` : "";
      return api.get<ErrorAnalyticsResponse>(`/analytics/errors${params}`);
    },
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 2,
  });
}

export function useStuckWorkflows() {
  return useQuery({
    queryKey: analyticsKeys.stuckWorkflows(),
    queryFn: () => api.get<StuckWorkflowsResponse>("/analytics/stuck-workflows"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 2,
  });
}

// ── Chart Data Hooks ─────────────────────────────────────────────

export function useUploadTrend(days?: number) {
  return useQuery({
    queryKey: analyticsKeys.uploadTrend(days ?? 30),
    queryFn: () => {
      const p = days ? `?days=${days}` : "";
      return api.get<{ day: string; count: number }[]>(`/analytics/upload-trend${p}`);
    },
    staleTime: 120_000,
    gcTime: 10 * 60_000,
    retry: 2,
  });
}

export function useRiskDistribution() {
  return useQuery({
    queryKey: analyticsKeys.riskDistribution(),
    queryFn: () => api.get<{ level: string; count: number }[]>("/analytics/risk-distribution"),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
    retry: 2,
  });
}

export function useFindingsByClause() {
  return useQuery({
    queryKey: analyticsKeys.findingsByClause(),
    queryFn: () => api.get<{ clause_type: string; count: number }[]>("/analytics/findings-by-clause"),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
    retry: 2,
  });
}

export function useAiCostTrend(days?: number) {
  return useQuery({
    queryKey: analyticsKeys.aiCostTrend(days ?? 30),
    queryFn: () => {
      const p = days ? `?days=${days}` : "";
      return api.get<{ day: string; runs: number; tokens: number; cost: number }[]>(`/analytics/ai-cost-trend${p}`);
    },
    staleTime: 120_000,
    gcTime: 10 * 60_000,
    retry: 2,
  });
}

export function useReviewAging() {
  return useQuery({
    queryKey: analyticsKeys.reviewAging(),
    queryFn: () => api.get<{ bucket: string; count: number }[]>("/analytics/review-aging"),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
    retry: 2,
  });
}

export function useExecutiveSummary() {
  return useQuery({
    queryKey: analyticsKeys.executiveSummary(),
    queryFn: () => api.get<{
      total_contracts: number;
      critical_contracts: number;
      high_risk_clause_types: number;
      missing_clause_findings: number;
      avg_review_sla_days: number;
      avg_risk_score: number;
      portfolio_risk: string;
    }>("/analytics/executive-summary"),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
    retry: 2,
  });
}

// ── Prediction Hooks ────────────────────────────────────────────

export function useStageDurationPercentiles() {
  return useQuery({
    queryKey: [...analyticsKeys.all, "predict", "stage-durations"],
    queryFn: () => api.get<Record<string, { p50: number; p75: number; p95: number }>>("/analytics/predict/stage-durations"),
    staleTime: 300_000,
    gcTime: 10 * 60_000,
  });
}

export function usePredictBottlenecks() {
  return useQuery({
    queryKey: [...analyticsKeys.all, "predict", "bottlenecks"],
    queryFn: () => api.get<{
      bottlenecks: Array<{ stage: string; review_id: string; severity: string; message: string }>;
      summary: { total_at_risk: number; critical_count: number };
    }>("/analytics/predict/bottlenecks"),
    staleTime: 120_000,
    gcTime: 5 * 60_000,
  });
}

export function useReviewerWorkload() {
  return useQuery({
    queryKey: [...analyticsKeys.all, "predict", "reviewer-workload"],
    queryFn: () => api.get<{
      reviewers: Array<{
        reviewer: string;
        active_count: number;
        completed_count: number;
        overload_probability: number;
        avg_completion_hours: number;
        predicted_backlog_hours: number;
      }>;
    }>("/analytics/predict/reviewer-workload"),
    staleTime: 120_000,
    gcTime: 5 * 60_000,
  });
}

export function useBatchSlaBreaches(limit?: number) {
  return useQuery({
    queryKey: [...analyticsKeys.all, "predict", "batch-sla-breaches", { limit }],
    queryFn: () => {
      const p = limit ? `?limit=${limit}` : "";
      return api.get<Array<{
        review_id: string;
        breach_probability: number;
        risk_score: number | null;
        priority: string;
        elapsed_hours: number;
        sla_deadline: string | null;
      }>>(`/analytics/predict/batch-sla-breaches${p}`);
    },
    staleTime: 120_000,
    gcTime: 5 * 60_000,
  });
}

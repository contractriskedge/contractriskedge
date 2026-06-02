/**
 * Executive API — unified aggregation layer for the Executive Command Center.
 *
 * Aggregates data from multiple backend endpoints into a single executive view.
 * This is the ONLY file that orchestrates executive data — widgets never call APIs directly.
 */

"use client";

import { api } from "@/services/api/client";
import type { ExecutiveDashboardData, ExecutiveKpi, WidgetDataMap } from "./executiveTypes";

const EXECUTIVE_BASE = "/analytics/executive";

// ── Primary Executive Dashboard ────────────────────────────────────

export async function fetchExecutiveDashboard(params?: {
  period_days?: number;
  include_trends?: boolean;
}): Promise<ExecutiveDashboardData> {
  const searchParams = new URLSearchParams();
  if (params?.period_days) searchParams.set("period_days", String(params.period_days));
  if (params?.include_trends !== undefined) searchParams.set("include_trends", String(params.include_trends));

  const qs = searchParams.toString();
  return api.get<ExecutiveDashboardData>(`${EXECUTIVE_BASE}/dashboard${qs ? `?${qs}` : ""}`);
}

// ── Individual Data Domain Endpoints ───────────────────────────────

export async function fetchPortfolioSummary(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`${EXECUTIVE_BASE}/portfolio-summary${qs}`);
}

export async function fetchCycleTimeAnalytics(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`${EXECUTIVE_BASE}/cycle-time${qs}`);
}

export async function fetchReviewerEfficiency(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`${EXECUTIVE_BASE}/reviewer-efficiency${qs}`);
}

export async function fetchSLARiskOverview(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`${EXECUTIVE_BASE}/sla-risk${qs}`);
}

export async function fetchNegotiationTrends(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`${EXECUTIVE_BASE}/negotiation-trends${qs}`);
}

export async function fetchContractExposure(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`${EXECUTIVE_BASE}/contract-exposure${qs}`);
}

export async function fetchThroughputBottlenecks(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`${EXECUTIVE_BASE}/throughput-bottlenecks${qs}`);
}

// ── Health Score ───────────────────────────────────────────────────

export async function fetchHealthScore(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`/analytics/health-score${qs}`);
}

export async function fetchHealthScoreHistory(params?: { period_days?: number }) {
  const qs = params?.period_days ? `?period_days=${params.period_days}` : "";
  return api.get(`/analytics/health-score/history${qs}`);
}

// ── Executive Report ───────────────────────────────────────────────

export async function generateExecutiveReport(params: {
  period_days: number;
  include_trends?: boolean;
  include_recommendations?: boolean;
}) {
  return api.post(`${EXECUTIVE_BASE}/report`, params);
}

// ── Anomaly Detection ──────────────────────────────────────────────

export async function fetchAnomalies(params?: {
  period_hours?: number;
  severity?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.period_hours) searchParams.set("period_hours", String(params.period_hours));
  if (params?.severity) searchParams.set("severity", params.severity);
  const qs = searchParams.toString();
  return api.get(`/analytics/anomalies${qs ? `?${qs}` : ""}`);
}

/**
 * Executive Analytics API service — business intelligence dashboards.
 *
 * Sprint 7 Priority 4.
 *
 * Provides typed API client methods for:
 * - Executive KPI dashboard
 * - Trend data with historical comparison
 * - Risk heatmaps by department/vendor/region
 * - Bottleneck identification
 * - SLA breach forecasting
 * - Reviewer efficiency metrics
 * - Exportable reports
 *
 * Usage:
 *   import { executiveService } from '@/services/api/executive';
 *   const dashboard = await executiveService.getDashboard({ period: 'last_30_days' });
 */

"use client";

import { api } from "@/services/api/client";

// ── Types ─────────────────────────────────────────────────────────

export type TimePeriod = "today" | "last_7_days" | "last_30_days" | "last_quarter" | "last_year" | "custom";

export type TrendDirection = "up" | "down" | "stable";

export type SeverityLevel = "positive" | "neutral" | "negative";

export interface DateRange {
  start: string;
  end: string;
}

export interface ExecutiveKPI {
  id: string;
  label: string;
  value: number;
  format: "number" | "currency" | "percentage" | "duration" | "ratio";
  previous_value: number | null;
  change_pct: number | null;
  trend: TrendDirection;
  severity: SeverityLevel;
  tooltip: string;
}

export interface TrendDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface TrendSeries {
  id: string;
  label: string;
  data: TrendDataPoint[];
  color?: string;
}

export interface TrendData {
  series: TrendSeries[];
  period: DateRange;
  comparison_period?: DateRange;
  change_pct: number | null;
}

export interface RiskHeatmapCell {
  row: string; // e.g., department name
  column: string; // e.g., risk category
  value: number;
  count: number;
  severity: "low" | "medium" | "high" | "critical";
}

export interface RiskHeatmap {
  title: string;
  rows: string[];
  columns: string[];
  cells: RiskHeatmapCell[];
  dateRange: DateRange;
}

export interface Bottleneck {
  stage: string;
  avg_duration_hours: number;
  median_duration_hours: number;
  p95_duration_hours: number;
  queue_size: number;
  trend: TrendDirection;
  severity: "low" | "medium" | "high";
}

export interface Forecast {
  metric: string;
  current_value: number;
  forecasted_value: number;
  confidence_interval: { lower: number; upper: number };
  forecast_date: string;
  model: string;
}

export interface ReviewerEfficiency {
  reviewer_id: string;
  reviewer_name: string;
  reviews_completed: number;
  avg_review_time_hours: number;
  avg_findings_per_review: number;
  accuracy_rate: number; // 0-1
  workload_score: number; // 0-100
  trend: TrendDirection;
}

export interface ExecutiveDashboard {
  period: DateRange;
  kpis: ExecutiveKPI[];
  trends: TrendData[];
  heatmaps: RiskHeatmap[];
  bottlenecks: Bottleneck[];
  forecasts: Forecast[];
  reviewer_efficiency: ReviewerEfficiency[];
  generated_at: string;
}

export interface ReportExportRequest {
  format: "pdf" | "csv" | "xlsx";
  sections: string[];
  dateRange: DateRange;
  filters?: Record<string, unknown>;
}

// ── Query Key Factory ─────────────────────────────────────────────

export const executiveKeys = {
  all: ["executive"] as const,
  dashboard: (period: TimePeriod) => [...executiveKeys.all, "dashboard", period] as const,
  trends: (metric: string, period: TimePeriod) => [...executiveKeys.all, "trends", metric, period] as const,
  heatmap: (dimension: string, period: TimePeriod) => [...executiveKeys.all, "heatmap", dimension, period] as const,
  bottlenecks: () => [...executiveKeys.all, "bottlenecks"] as const,
  forecasts: (metric: string) => [...executiveKeys.all, "forecasts", metric] as const,
  efficiency: () => [...executiveKeys.all, "efficiency"] as const,
};

// ── Service ───────────────────────────────────────────────────────

export const executiveService = {
  /** Get the full executive dashboard */
  getDashboard: (params: { period?: TimePeriod; start?: string; end?: string; tenant_id?: string }) =>
    api.get<ExecutiveDashboard>("/executive/dashboard", params as Record<string, unknown>),

  /** Get trend data for a specific metric */
  getTrends: (metric: string, params: { period?: TimePeriod; start?: string; end?: string }) =>
    api.get<TrendData>(`/executive/trends/${metric}`, params as Record<string, unknown>),

  /** Get risk heatmap data */
  getHeatmap: (dimension: string, params: { period?: TimePeriod; start?: string; end?: string }) =>
    api.get<RiskHeatmap>(`/executive/heatmap/${dimension}`, params as Record<string, unknown>),

  /** Get workflow bottlenecks */
  getBottlenecks: () => api.get<{ data: Bottleneck[] }>("/executive/bottlenecks"),

  /** Get SLA breach forecasts */
  getForecasts: (metric?: string) =>
    api.get<{ data: Forecast[] }>("/executive/forecasts", metric ? { metric } as Record<string, unknown> : undefined),

  /** Get reviewer efficiency metrics */
  getReviewerEfficiency: (params?: { period?: TimePeriod; limit?: number }) =>
    api.get<{ data: ReviewerEfficiency[] }>("/executive/efficiency", params as Record<string, unknown>),

  /** Export a report */
  exportReport: (body: ReportExportRequest) =>
    api.post<{ download_url: string; expires_at: string }>("/executive/export", body),
};

/**
 * Executive queries — TanStack Query hooks for the Executive Command Center.
 *
 * All executive data fetching is centralized here.
 * Widgets receive data through props only — they never fetch directly.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  fetchExecutiveDashboard,
  fetchHealthScore,
  fetchHealthScoreHistory,
  fetchAnomalies,
} from "./executiveApi";

export const executiveKeys = {
  all: ["executive"] as const,
  dashboard: (periodDays?: number) => [...executiveKeys.all, "dashboard", { periodDays }] as const,
  healthScore: (periodDays?: number) => [...executiveKeys.all, "health-score", { periodDays }] as const,
  healthScoreHistory: (periodDays?: number) => [...executiveKeys.all, "health-score-history", { periodDays }] as const,
  anomalies: (periodHours?: number) => [...executiveKeys.all, "anomalies", { periodHours }] as const,
};

// ── Master Dashboard Query ─────────────────────────────────────────
// Fetches ALL executive data in one request for optimal performance.

export function useExecutiveDashboard(periodDays: number = 30) {
  return useQuery({
    queryKey: executiveKeys.dashboard(periodDays),
    queryFn: () => fetchExecutiveDashboard({ period_days: periodDays, include_trends: true }),
    staleTime: 60_000,        // 1 min — executive data refreshes moderately
    gcTime: 5 * 60_000,       // 5 min cache
    refetchInterval: 30_000,  // Poll every 30s for live updates
    retry: 3,
  });
}

// ── Individual Domain Queries ──────────────────────────────────────
// For components that need specific slices without the full dashboard.

export function useExecutiveHealthScore(periodDays: number = 7) {
  return useQuery({
    queryKey: executiveKeys.healthScore(periodDays),
    queryFn: () => fetchHealthScore({ period_days: periodDays }),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useExecutiveHealthScoreHistory(periodDays: number = 30) {
  return useQuery({
    queryKey: executiveKeys.healthScoreHistory(periodDays),
    queryFn: () => fetchHealthScoreHistory({ period_days: periodDays }),
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
  });
}

export function useExecutiveAnomalies(periodHours: number = 24) {
  return useQuery({
    queryKey: executiveKeys.anomalies(periodHours),
    queryFn: () => fetchAnomalies({ period_hours: periodHours }),
    staleTime: 30_000,
    gcTime: 2 * 60_000,
    refetchInterval: 30_000,
  });
}

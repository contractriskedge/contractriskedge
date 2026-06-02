/**
 * Benchmarks query hooks — TanStack Query wrappers for benchmarks API.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  fetchBenchmarkDashboard,
  fetchIndustryBenchmarks,
} from "@/services/api/benchmarks";

export const benchmarkKeys = {
  all: ["benchmarks"] as const,
  dashboard: () => [...benchmarkKeys.all, "dashboard"] as const,
  clauses: (industry?: string) => [...benchmarkKeys.all, "clauses", { industry }] as const,
};

export function useBenchmarkDashboard() {
  return useQuery({
    queryKey: benchmarkKeys.dashboard(),
    queryFn: fetchBenchmarkDashboard,
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
  });
}

export function useIndustryBenchmarks(industry?: string) {
  return useQuery({
    queryKey: benchmarkKeys.clauses(industry),
    queryFn: () => fetchIndustryBenchmarks(industry),
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
  });
}

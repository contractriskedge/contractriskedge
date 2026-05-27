"use client";

import { useState, useEffect, useCallback } from "react";
import { getAuthToken, getBenchmarkDashboard, listBenchmarkCorpora, seedBenchmarkData } from "@/lib/api";
import { benchmarkKpis as mockKpis, clauseBenchmarks as mockClauseBenchmarks, industryComparisons as mockIndustryComparisons } from "./mockData";
import type { ClauseBenchmark, BenchmarkKpi as BenchmarkKpiType, IndustryComparison as IndustryComparisonType } from "./types";
import type { BenchmarkDashboardData, BenchmarkCorpus } from "@/lib/api";

interface BenchmarkDataState {
  loading: boolean;
  error: string | null;
  kpis: BenchmarkKpiType[];
  clauseBenchmarks: ClauseBenchmark[];
  industryComparisons: IndustryComparisonType[];
  corpora: BenchmarkCorpus[];
  seeded: boolean;
}

export function useBenchmarkData(): BenchmarkDataState & { refresh: () => void; seedData: () => Promise<void> } {
  const [state, setState] = useState<BenchmarkDataState>({
    loading: true,
    error: null,
    kpis: mockKpis,
    clauseBenchmarks: mockClauseBenchmarks,
    industryComparisons: mockIndustryComparisons,
    corpora: [],
    seeded: false,
  });

  const fetchData = useCallback(async () => {
    try {
      const token = await getAuthToken();

      // Fetch dashboard data and corpora in parallel
      const [dashboard, corporaResult] = await Promise.allSettled([
        getBenchmarkDashboard(token),
        listBenchmarkCorpora(token),
      ]);

      const kpis = dashboard.status === "fulfilled"
        ? dashboard.value.kpis.map((k: any) => ({
            id: k.label.toLowerCase().replace(/\s+/g, "_"),
            label: k.label,
            value: k.value,
            trend: k.trend,
            trendDirection: k.trend_direction as "up" | "down" | "neutral",
            icon: "BarChart3",
            color: k.severity === "warning" ? "text-amber-500" : k.severity === "success" ? "text-green-500" : "text-blue-500",
            severity: k.severity as "critical" | "warning" | "success" | "info",
            sparklineData: [],
            tooltip: k.tooltip,
          }))
        : mockKpis;

      setState({
        loading: false,
        error: null,
        kpis,
        clauseBenchmarks: mockClauseBenchmarks, // Keep mock data for chart detail until real scoring exists
        industryComparisons: mockIndustryComparisons,
        corpora: corporaResult.status === "fulfilled" ? corporaResult.value.items : [],
        seeded: corporaResult.status === "fulfilled" && corporaResult.value.total > 0,
      });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load benchmark data",
      }));
    }
  }, []);

  const seedData = useCallback(async () => {
    try {
      const token = await getAuthToken();
      const result = await seedBenchmarkData(token);
      setState((prev) => ({ ...prev, seeded: true }));
      await fetchData(); // Refresh after seeding
    } catch (err) {
      console.error("Failed to seed benchmark data:", err);
    }
  }, [fetchData]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { ...state, refresh: fetchData, seedData };
}

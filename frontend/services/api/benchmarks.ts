/**
 * Benchmarks API service — real API client for benchmark/comparison operations.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { api } from "@/services/api/client";

export interface BenchmarkKpi {
  label: string;
  value: number;
  percentile: number;
  industry_avg: number;
  trend: "up" | "down" | "neutral";
}

export interface ClauseBenchmark {
  clause_type: string;
  your_score: number;
  industry_avg: number;
  top_quartile: number;
  risk_level: "low" | "medium" | "high";
  sample_size: number;
}

export interface IndustryCorpus {
  id: string;
  industry: string;
  clause_count: number;
  avg_risk_score: number;
  last_updated: string;
}

export interface BenchmarkDashboardData {
  kpis: BenchmarkKpi[];
  clause_benchmarks: ClauseBenchmark[];
  industry_corpora: IndustryCorpus[];
  total_clauses_analyzed: number;
  industries_covered: string[];
}

export async function fetchBenchmarkDashboard(): Promise<BenchmarkDashboardData> {
  return api.get<BenchmarkDashboardData>("/benchmarks/dashboard");
}

export async function fetchIndustryBenchmarks(industry?: string): Promise<ClauseBenchmark[]> {
  const qs = industry ? `?industry=${encodeURIComponent(industry)}` : "";
  return api.get<ClauseBenchmark[]>(`/benchmarks/clauses${qs}`);
}

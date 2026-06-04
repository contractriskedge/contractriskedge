"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { BarChart3, Download, RefreshCw, Search, Database, Loader2, AlertCircle } from "lucide-react";
import { BenchmarkKpiCards } from "./BenchmarkKpiCards";
import { ClauseBenchmarkChart, DeviationHeatmap, IndustryComparisonChart, VendorAggressivenessChart, ComplianceBenchmarkChart, ClauseFrequencyChart } from "./BenchmarkCharts";
import { BenchmarkAiInsights } from "./AiInsights";
import { NegotiationIntelPanel, VendorBenchmarkTable } from "./NegotiationIntel";
import { BenchmarkDetailDrawer } from "./BenchmarkDetailDrawer";
import { BenchmarkFilterBar } from "./BenchmarkFilterBar";
import { useBenchmarkDashboard } from "@/services/hooks/useBenchmarks";
import type { ClauseBenchmark, BenchmarkFilterState } from "./types";

const defaultFilters: BenchmarkFilterState = {
  industry: "", geography: "", contractType: "", clauseCategory: "", vendorType: "", companySize: "", regulation: "", dateRange: "",
};

export function BenchmarkPage() {
  const [filters, setFilters] = useState<BenchmarkFilterState>({ ...defaultFilters });
  const [selectedBenchmark, setSelectedBenchmark] = useState<ClauseBenchmark | null>(null);
  const { data: dashboardData, isLoading, error, refetch } = useBenchmarkDashboard();

  const benchmarkKpis = dashboardData?.kpis ?? [];
  const clauseBenchmarks = dashboardData?.clause_benchmarks ?? [];
  const industryComparisons = dashboardData?.industry_corpora ?? [];
  const marketInsights = [];
  const vendorBenchmarks = [];
  const negotiationIntel = [];
  const complianceBenchmarks = [];
  const clauseLibrary = [];

  const handleFilterChange = useCallback((key: keyof BenchmarkFilterState, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);
  const resetFilters = useCallback(() => setFilters({ ...defaultFilters }), []);

  // Loading state
  if (isLoading && clauseBenchmarks.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-gold-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading benchmark data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && clauseBenchmarks.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load benchmark data</p>
          <p className="text-xs text-gray-500 mb-4">{(error as Error)?.message || "An unexpected error occurred"}</p>
          <button onClick={() => refetch()} className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-800 flex items-center justify-center shadow-sm">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Market Benchmark Intelligence</h1>
            <p className="text-xs text-gray-500 mt-0.5">AI-powered contract market analysis and clause benchmarking</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <Search className="w-3.5 h-3.5" /> Smart Search
          </button>
          <button onClick={refetch} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" /> Export Report
          </button>
        </div>
      </motion.div>

      {/* KPI Row */}
      <BenchmarkKpiCards metrics={benchmarkKpis} />

      {/* Loading / Error / Seed states */}
      {isLoading && (
        <div className="flex items-center justify-center py-8 text-gray-400">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading benchmark data...
        </div>
      )}
      {error && (
        <div className="flex items-center justify-between px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
          <span>{error?.message || "An error occurred loading benchmark data"}</span>
          <button onClick={refetch} className="px-3 py-1 text-xs font-medium bg-amber-100 rounded-md hover:bg-amber-200 transition-colors">
            Retry
          </button>
        </div>
      )}
      {!isLoading && !error && benchmarkKpis.length === 0 && clauseBenchmarks.length === 0 && (
        <div className="flex items-center justify-between px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-blue-700">
            <Database className="w-4 h-4" />
            <span>No benchmark data available. Upload and score contracts to see market comparisons.</span>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <BenchmarkFilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} />

      {/* Section 1: Clause Benchmark Analytics */}
      <div>
        <h2 className="text-sm font-semibold text-navy-900 mb-3">Clause Benchmark Analytics</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ClauseBenchmarkChart data={clauseBenchmarks} />
          <DeviationHeatmap data={clauseBenchmarks} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <IndustryComparisonChart data={industryComparisons} />
          <ClauseFrequencyChart data={clauseLibrary} />
        </div>
      </div>

      {/* Section 2: AI Insights + Negotiation Intel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <BenchmarkAiInsights insights={marketInsights} />
        </div>
        <div className="lg:col-span-1">
          <NegotiationIntelPanel data={negotiationIntel} />
        </div>
      </div>

      {/* Section 3: Compliance + Vendor */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ComplianceBenchmarkChart data={complianceBenchmarks} />
        <VendorAggressivenessChart data={vendorBenchmarks.map((v) => ({ vendor: v.vendor, score: v.aggressivenessScore }))} />
      </div>

      {/* Section 4: Vendor Benchmark Table */}
      <VendorBenchmarkTable data={vendorBenchmarks} />

      {/* Section 5: Clause Benchmark Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="text-xs font-semibold text-navy-900">Clause Benchmark Detail</h3>
          <p className="text-[10px] text-gray-500 mt-0.5">Click a row to view detailed benchmark analysis</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Clause Type</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Your Score</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Market Median</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Deviation</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Percentile</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Confidence</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Samples</th>
                <th className="text-center py-2.5 px-3 text-[10px] font-semibold text-gray-500 uppercase">Trend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {clauseBenchmarks.map((cb, i) => (
                <motion.tr key={cb.clauseType} initial={{ opacity: 0, y: 2 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}
                  className="hover:bg-navy-50/40 transition-colors cursor-pointer" onClick={() => setSelectedBenchmark(cb)}>
                  <td className="py-2.5 px-3 font-medium text-gray-800 text-[11px]">{cb.clauseType}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                      cb.yourScore >= 7 ? "bg-red-50 text-red-700" : cb.yourScore >= 5 ? "bg-orange-50 text-orange-700" : cb.yourScore >= 3 ? "bg-yellow-50 text-yellow-700" : "bg-green-50 text-green-700"
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${cb.yourScore >= 7 ? "bg-red-500" : cb.yourScore >= 5 ? "bg-orange-500" : cb.yourScore >= 3 ? "bg-yellow-500" : "bg-green-500"}`} />
                      {cb.yourScore}/10
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center text-gray-600">{cb.marketMedian}/10</td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={`font-medium ${cb.direction === "far_above" ? "text-red-600" : cb.direction === "above_market" ? "text-orange-600" : cb.direction === "at_market" ? "text-gray-600" : "text-green-600"}`}>
                      {cb.deviationPercent > 0 ? "+" : ""}{cb.deviationPercent.toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${cb.percentile >= 75 ? "bg-red-500" : cb.percentile >= 50 ? "bg-yellow-500" : "bg-green-500"}`} style={{ width: `${cb.percentile}%` }} />
                      </div>
                      <span className="text-[10px] text-gray-500 tabular-nums">{cb.percentile}th</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-center text-gray-600">{cb.confidence}%</td>
                  <td className="py-2.5 px-3 text-center text-gray-500 tabular-nums">{cb.sampleSize.toLocaleString()}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={`text-[10px] font-medium ${cb.trend > 0 ? "text-red-500" : "text-green-500"}`}>
                      {cb.trend > 0 ? "↑" : "↓"} {Math.abs(cb.trend).toFixed(1)}%
                    </span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Drawer */}
      <BenchmarkDetailDrawer benchmark={selectedBenchmark} onClose={() => setSelectedBenchmark(null)} />
    </div>
  );
}

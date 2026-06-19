"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { BarChart3, Download, RefreshCw, Search, Database, Loader2, AlertCircle, TrendingUp, TrendingDown, Minus, Target, Award, AlertTriangle, Lightbulb } from "lucide-react";
import { BenchmarkKpiCards } from "./BenchmarkKpiCards";
import { ClauseBenchmarkChart, DeviationHeatmap, IndustryComparisonChart, VendorAggressivenessChart, ComplianceBenchmarkChart, ClauseFrequencyChart } from "./BenchmarkCharts";
import { BenchmarkAiInsights } from "./AiInsights";
import { NegotiationIntelPanel, VendorBenchmarkTable } from "./NegotiationIntel";
import { BenchmarkDetailDrawer } from "./BenchmarkDetailDrawer";
import { BenchmarkFilterBar } from "./BenchmarkFilterBar";
import { useBenchmarkDashboard } from "@/services/hooks/useBenchmarks";
import type { ClauseBenchmark, BenchmarkFilterState, MarketInsight, VendorBenchmark, NegotiationIntel, ComplianceBenchmark, ClauseLibrary } from "./types";

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
  // Derive market insights from clause benchmarks when no dedicated endpoint
  const marketInsights: MarketInsight[] = clauseBenchmarks.length > 0
    ? clauseBenchmarks
        .filter((cb) => cb.deviation > 15)
        .map((cb) => ({
          id: `insight-${cb.clauseType}`,
          title: `${cb.clauseType} — ${cb.deviationPercent > 0 ? "Above" : "Below"} Market`,
          description: `Your ${cb.clauseType} clause scores ${cb.yourScore} vs market median ${cb.marketMedian} (${cb.deviationPercent > 0 ? "+" : ""}${cb.deviationPercent}% deviation)`,
          severity: cb.deviationPercent > 30 ? "critical" : cb.deviationPercent > 15 ? "warning" : "info",
          confidence: cb.confidence,
          percentile: cb.percentile,
          affectedClauses: [cb.clauseType],
          recommendation: cb.deviationPercent > 0
            ? `Consider negotiating ${cb.clauseType} terms closer to market median (${cb.marketMedian})`
            : `Your ${cb.clauseType} terms are favorable — ensure they remain competitive`,
          category: cb.category,
          quickActions: [{ label: "View Details", action: `view-${cb.clauseType}` }],
        }))
    : [];
  const vendorBenchmarks: VendorBenchmark[] = [];
  const negotiationIntel: NegotiationIntel[] = clauseBenchmarks.length > 0
    ? clauseBenchmarks.slice(0, 5).map((cb) => ({
        clauseType: cb.clauseType,
        leverageScore: Math.round((1 - Math.abs(cb.deviationPercent) / 100) * 100),
        marketPosition: cb.deviation > 0
          ? `Your ${cb.clauseType} is ${cb.deviationPercent}% above market median`
          : `Your ${cb.clauseType} is ${Math.abs(cb.deviationPercent)}% below market median`,
        recommendedPosition: `Target ${cb.clauseType} terms near P${Math.min(75, cb.percentile + 10)} market level`,
        fallbackPositions: [
          `Accept market median of ${cb.marketMedian}`,
          `Propose ${Math.round((cb.yourScore + cb.marketMedian) / 2)} as compromise`,
        ],
        vendorFavorability: cb.direction === "above_market" || cb.direction === "far_above" ? 75 : 40,
        confidence: cb.confidence,
      }))
    : [];
  const complianceBenchmarks: ComplianceBenchmark[] = [];
  const clauseLibrary: ClauseLibrary[] = clauseBenchmarks.length > 0
    ? clauseBenchmarks.map((cb) => ({
        clauseType: cb.clauseType,
        frequency: cb.sampleSize,
        trend: cb.trend,
        riskScore: Math.round((1 - cb.percentile / 100) * 10),
        industryStandard: cb.marketMedian.toString(),
        commonVariations: Math.max(1, Math.round(cb.sampleSize / 10)),
        lastUpdated: new Date().toISOString().split("T")[0],
      }))
    : [];

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

      {/* Market Position Summary — from real benchmark data */}
      {clauseBenchmarks.length > 0 && (() => {
        const avgPercentile = clauseBenchmarks.reduce((s, cb) => s + cb.percentile, 0) / clauseBenchmarks.length;
        const avgDeviation = clauseBenchmarks.reduce((s, cb) => s + cb.deviationPercent, 0) / clauseBenchmarks.length;
        const aboveMarket = clauseBenchmarks.filter(cb => cb.direction === "far_above" || cb.direction === "above_market").length;
        const belowMarket = clauseBenchmarks.filter(cb => cb.direction === "far_below" || cb.direction === "below_market").length;
        const atMarket = clauseBenchmarks.length - aboveMarket - belowMarket;
        const topClause = clauseBenchmarks.reduce((max, cb) => Math.abs(cb.deviationPercent) > Math.abs(max.deviationPercent) ? cb : max, clauseBenchmarks[0]);
        const totalSamples = clauseBenchmarks.reduce((s, cb) => s + cb.sampleSize, 0);

        return (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* Market Position */}
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-emerald-500" />
                <span className="text-[10px] font-semibold text-gray-500 uppercase">Market Position</span>
              </div>
              <p className="text-2xl font-bold text-navy-900 dark:text-white">{avgPercentile.toFixed(0)}<span className="text-sm font-medium text-gray-400">th</span></p>
              <p className="text-xs text-gray-500 mt-0.5">Average percentile across {clauseBenchmarks.length} clause categories</p>
              <div className="mt-2 flex items-center gap-2 text-xs">
                <span className="text-emerald-600 font-medium">{aboveMarket} above</span>
                <span className="text-gray-300">·</span>
                <span className="text-gray-500">{atMarket} at market</span>
                <span className="text-gray-300">·</span>
                <span className="text-blue-600 font-medium">{belowMarket} below</span>
              </div>
            </div>

            {/* Overall Deviation */}
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
              <div className="flex items-center gap-2 mb-2">
                <Award className="w-4 h-4 text-amber-500" />
                <span className="text-[10px] font-semibold text-gray-500 uppercase">Overall Deviation</span>
              </div>
              <p className={`text-2xl font-bold ${avgDeviation > 0 ? "text-red-500" : "text-green-500"}`}>
                {avgDeviation > 0 ? "+" : ""}{avgDeviation.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {avgDeviation > 5 ? "Your contracts are more aggressive than market" :
                 avgDeviation < -5 ? "Your contracts are more favorable than market" :
                 "Your contracts are near market average"}
              </p>
            </div>

            {/* Top Outlier */}
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-purple-500" />
                <span className="text-[10px] font-semibold text-gray-500 uppercase">Top Outlier</span>
              </div>
              <p className="text-lg font-bold text-navy-900 dark:text-white truncate">{topClause.clauseType}</p>
              <p className={`text-sm font-semibold ${topClause.deviationPercent > 0 ? "text-red-500" : "text-green-500"}`}>
                {topClause.deviationPercent > 0 ? "+" : ""}{topClause.deviationPercent.toFixed(0)}% vs market
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{topClause.percentile}th percentile</p>
            </div>

            {/* Sample Size */}
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
              <div className="flex items-center gap-2 mb-2">
                <Database className="w-4 h-4 text-blue-500" />
                <span className="text-[10px] font-semibold text-gray-500 uppercase">Benchmark Coverage</span>
              </div>
              <p className="text-2xl font-bold text-navy-900 dark:text-white">{totalSamples.toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-0.5">Contract samples across {clauseBenchmarks.length} clause types</p>
            </div>
          </div>
        );
      })()}

      {/* Clause Outlier Analysis — top deviations */}
      {clauseBenchmarks.length > 0 && (() => {
        const sortedByDeviation = [...clauseBenchmarks].sort((a, b) => Math.abs(b.deviationPercent) - Math.abs(a.deviationPercent));
        const topDeviations = sortedByDeviation.slice(0, 5);

        return (
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-orange-500" />
              <span className="text-xs font-semibold text-gray-500 uppercase">Clause Outlier Analysis</span>
            </div>
            <div className="space-y-2">
              {topDeviations.map((cb) => {
                const isAggressive = cb.deviationPercent > 0;
                return (
                  <div key={cb.clauseType} className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50 dark:bg-navy-700">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-navy-900 dark:text-white">{cb.clauseType}</p>
                      <p className="text-[10px] text-gray-500">
                        Your score: {cb.yourScore}/10 · Market: {cb.marketMedian}/10 · {cb.percentile}th percentile
                      </p>
                    </div>
                    <div className="flex items-center gap-3 ml-3">
                      <div className="w-20 h-2 bg-gray-200 dark:bg-navy-600 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isAggressive ? "bg-red-500" : "bg-green-500"}`}
                          style={{ width: `${Math.min(Math.abs(cb.deviationPercent), 100)}%` }}
                        />
                      </div>
                      <span className={`text-xs font-semibold ${isAggressive ? "text-red-600" : "text-green-600"} w-16 text-right`}>
                        {isAggressive ? "+" : ""}{cb.deviationPercent.toFixed(0)}%
                      </span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                        isAggressive ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
                      }`}>
                        {isAggressive ? "Aggressive" : "Favorable"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* Benchmark Recommendations */}
      {clauseBenchmarks.length > 0 && (() => {
        const highDeviations = clauseBenchmarks.filter(cb => Math.abs(cb.deviationPercent) > 15).slice(0, 3);
        if (highDeviations.length === 0) return null;

        return (
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-semibold text-gray-500 uppercase">Benchmark Recommendations</span>
            </div>
            <div className="space-y-2">
              {highDeviations.map((cb) => {
                const isAggressive = cb.deviationPercent > 0;
                return (
                  <div key={cb.clauseType} className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-900/20">
                    <Lightbulb className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-navy-900 dark:text-white">{cb.clauseType}</p>
                      <p className="text-[10px] text-gray-600 dark:text-gray-400 mt-0.5">
                        {isAggressive
                          ? `${cb.clauseType} exceeds market by ${cb.deviationPercent.toFixed(0)}%. Consider reviewing ${cb.clauseType.toLowerCase()} terms to align with market standards.`
                          : `${cb.clauseType} is ${Math.abs(cb.deviationPercent).toFixed(0)}% below market. Your current terms are favorable but may be leaving leverage on the table.`}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

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

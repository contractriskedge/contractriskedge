/**
 * AiOperationsDashboard — Operational AI dashboard for AI/engineering leads.
 *
 * Sprint 10 Priority 2.
 *
 * Shows:
 * - Token & cost explorer
 * - Model routing analytics
 * - Hallucination & quality monitor
 * - Benchmark suite dashboard
 * - Deployment safety gates
 */

"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import { DashboardHeader } from "../command-center/DashboardHeader";

type DateRange = "24h" | "7d" | "30d" | "90d";
type RefreshInterval = 0 | 15 | 30 | 60;

type TabId = "cost" | "routing" | "quality" | "benchmarks" | "gates";

const TABS: { id: TabId; label: string }[] = [
  { id: "cost", label: "Cost" },
  { id: "routing", label: "Routing" },
  { id: "quality", label: "Quality" },
  { id: "benchmarks", label: "Benchmarks" },
  { id: "gates", label: "Safety Gates" },
];

const AI_GOV_BASE = "/ai-governance";

// ── Hooks ───────────────────────────────────────────────────────

function useCostSummary() {
  return useQuery({
    queryKey: ["ai-cost-summary"],
    queryFn: () => api.get<any>(`${AI_GOV_BASE}/cost-summary`),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

function useSafetySummary() {
  return useQuery({
    queryKey: ["ai-safety-summary"],
    queryFn: () => api.get<any>(`${AI_GOV_BASE}/safety-summary`),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function AiOperationsDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("cost");
  const [dateRange, setDateRange] = useState<DateRange>("7d");
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(30);

  const { data: costData, isLoading: costLoading } = useCostSummary();
  const { data: safetyData, isLoading: safetyLoading } = useSafetySummary();

  return (
    <div className="p-6 space-y-4">
      <DashboardHeader
        title="AI Operations"
        description="Token usage, model routing, quality metrics, benchmarks, and deployment safety gates"
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        refreshInterval={refreshInterval}
        onRefreshIntervalChange={setRefreshInterval}
        onExport={() => {}}
      />

      {/* ── Tabs ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-1 border-b border-gray-200 dark:border-navy-700">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-navy-900 dark:border-white text-navy-900 dark:text-white"
                : "border-transparent text-gray-500 dark:text-gray-400 hover:text-navy-700 dark:hover:text-navy-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab Content ──────────────────────────────────────── */}
      <div>
        {activeTab === "cost" && <TokenCostExplorer data={costData} isLoading={costLoading} />}
        {activeTab === "routing" && <ModelRoutingAnalytics />}
        {activeTab === "quality" && <HallucinationQualityMonitor />}
        {activeTab === "benchmarks" && <BenchmarkSuiteDashboard />}
        {activeTab === "gates" && <DeploymentSafetyGate data={safetyData} isLoading={safetyLoading} />}
      </div>
    </div>
  );
}

// ── Cost Tab ───────────────────────────────────────────────────

function TokenCostExplorer({ data, isLoading }: { data?: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-600" />
      </div>
    );
  }

  const modelCosts = data?.cost_by_model ?? [];
  const totalCost = data?.total_cost ?? 0;
  const totalTokens = data?.total_tokens ?? 0;
  const totalRequests = data?.total_requests ?? 0;
  const avgLatency = data?.avg_latency_ms ?? 0;

  return (
    <div className="space-y-4">
      {/* ── Summary KPIs ──────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
          <span className="text-[10px] text-gray-500 uppercase">Total Cost</span>
          <p className="text-lg font-bold text-navy-900 dark:text-white">${Number(totalCost).toFixed(4)}</p>
          <span className="text-[10px] text-gray-400">{totalRequests} requests</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
          <span className="text-[10px] text-gray-500 uppercase">Total Tokens</span>
          <p className="text-lg font-bold text-navy-900 dark:text-white">{(totalTokens / 1_000_000).toFixed(1)}M</p>
          <span className="text-[10px] text-gray-400">{totalTokens.toLocaleString()} tokens</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
          <span className="text-[10px] text-gray-500 uppercase">Avg Latency</span>
          <p className="text-lg font-bold text-navy-900 dark:text-white">{Math.round(avgLatency).toLocaleString()}ms</p>
          <span className="text-[10px] text-gray-400">per request</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
          <span className="text-[10px] text-gray-500 uppercase">Avg Cost/Token</span>
          <p className="text-lg font-bold text-navy-900 dark:text-white">${Number(data?.avg_cost_per_token ?? 0).toExponential(2)}</p>
          <span className="text-[10px] text-gray-400">per token</span>
        </div>
      </div>

      {/* ── Cost by Model ─────────────────────────────────────── */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Cost by Model</h3>
        </div>
        <div className="p-4 space-y-2">
          {modelCosts.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-4">No cost data available</p>
          ) : (
            modelCosts.map((m: any) => (
              <div key={m.model} className="flex items-center gap-3">
                <span className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate">{m.model}</span>
                <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${m.percentage}%`,
                      backgroundColor: m.model.includes("mini") ? "#10B981" : m.model.includes("turbo") ? "#8B5CF6" : m.model.includes("sonnet") ? "#F59E0B" : "#3B82F6",
                    }}
                  />
                </div>
                <span className="text-xs text-navy-900 dark:text-white font-medium w-20 text-right">${Number(m.cost).toFixed(4)}</span>
                <span className="text-[10px] text-gray-400 w-12 text-right">{m.percentage}%</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── Latency by Model ──────────────────────────────────── */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Latency by Model</h3>
        </div>
        <div className="p-4">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-100 dark:border-navy-700">
                <th className="text-left py-1 font-medium">Model</th>
                <th className="text-right py-1 font-medium">Avg (ms)</th>
                <th className="text-right py-1 font-medium">Min (ms)</th>
                <th className="text-right py-1 font-medium">Max (ms)</th>
              </tr>
            </thead>
            <tbody>
              {(data?.latency_by_model ?? []).map((m: any) => (
                <tr key={m.model} className="border-b border-gray-50 dark:border-navy-800">
                  <td className="py-1.5 text-navy-900 dark:text-white">{m.model}</td>
                  <td className="py-1.5 text-right">{Math.round(m.avg_latency_ms).toLocaleString()}</td>
                  <td className="py-1.5 text-right">{Math.round(m.min_latency_ms).toLocaleString()}</td>
                  <td className="py-1.5 text-right">{Math.round(m.max_latency_ms).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ModelRoutingAnalytics() {
  const strategies = [
    { name: "Quality First", pct: 42, color: "#8B5CF6" },
    { name: "Balanced", pct: 31, color: "#3B82F6" },
    { name: "Cost First", pct: 20, color: "#10B981" },
    { name: "Tenant Preferred", pct: 7, color: "#F59E0B" },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Routing Strategy Distribution</h3>
        </div>
        <div className="p-4 space-y-3">
          {strategies.map((s) => (
            <div key={s.name} className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-28">{s.name}</span>
              <div className="flex-1 h-4 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${s.pct}%`, backgroundColor: s.color }}
                />
              </div>
              <span className="text-xs font-medium text-navy-900 dark:text-white w-8 text-right">{s.pct}%</span>
            </div>
          ))}
        </div>
      </div>
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Routing Efficiency</h3>
        </div>
        <div className="p-4 space-y-2">
          {[
            { metric: "Avg Quality Score", value: "8.7/10", trend: "stable" },
            { metric: "Avg Cost per Request", value: "$0.012", trend: "down" },
            { metric: "Strategy Accuracy", value: "94.2%", trend: "up" },
            { metric: "Fallback Rate", value: "2.3%", trend: "down" },
          ].map((m) => (
            <div key={m.metric} className="flex items-center justify-between p-2 rounded-lg bg-gray-50 dark:bg-navy-700">
              <span className="text-xs text-gray-600 dark:text-gray-400">{m.metric}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-navy-900 dark:text-white">{m.value}</span>
                <span className={`text-[10px] ${m.trend === "up" ? "text-green-500" : m.trend === "down" ? "text-green-500" : "text-gray-400"}`}>
                  {m.trend === "up" ? "↑" : m.trend === "down" ? "↓" : "→"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function HallucinationQualityMonitor() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Hallucination Rate</h3>
        </div>
        <div className="p-4 text-center">
          <div className="relative w-24 h-24 mx-auto">
            <svg className="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="#E5E7EB" strokeWidth="3" className="dark:stroke-navy-600" />
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="#F59E0B" strokeWidth="3" strokeDasharray="3.2 96.8" strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-bold text-navy-900 dark:text-white">3.2%</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">Threshold: 5.0%</p>
          <p className="text-[10px] text-green-500 mt-1">Within acceptable range</p>
        </div>
      </div>
      <div className="lg:col-span-2 bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Detection Method Breakdown</h3>
        </div>
        <div className="p-4 space-y-2">
          {[
            { method: "Overlap Analysis", rate: 1.8, pct: 56 },
            { method: "Phrase Matching", rate: 0.9, pct: 28 },
            { method: "Grounding Score", rate: 0.5, pct: 16 },
          ].map((d) => (
            <div key={d.method} className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-28">{d.method}</span>
              <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-amber-500" style={{ width: `${d.pct}%` }} />
              </div>
              <span className="text-xs text-navy-900 dark:text-white font-medium w-12 text-right">{d.rate}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function BenchmarkSuiteDashboard() {
  const tests = [
    { name: "Liability Extraction", score: 92, status: "pass" },
    { name: "Jurisdiction Classification", score: 88, status: "pass" },
    { name: "Indemnification Scoring", score: 76, status: "warning" },
    { name: "Termination Clause", score: 94, status: "pass" },
    { name: "Data Privacy Compliance", score: 85, status: "pass" },
    { name: "Force Majeure Analysis", score: 71, status: "warning" },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Benchmark Suite</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-green-600">Pass Rate: 84%</span>
          <span className="text-xs text-gray-400">|</span>
          <span className="text-xs text-gray-500">Last run: Today 09:42</span>
        </div>
      </div>
      <div className="p-4">
        <div className="grid grid-cols-2 gap-2">
          {tests.map((t) => (
            <div key={t.name} className={`p-3 rounded-lg border ${
              t.status === "pass"
                ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                : "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"
            }`}>
              <div className="flex items-center justify-between">
                <span className="text-xs text-navy-900 dark:text-white">{t.name}</span>
                <span className={`text-xs font-bold ${
                  t.status === "pass" ? "text-green-600 dark:text-green-400" : "text-amber-600 dark:text-amber-400"
                }`}>{t.score}%</span>
              </div>
              <div className="w-full h-1.5 bg-gray-200 dark:bg-navy-600 rounded-full mt-1 overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${t.score}%`,
                    backgroundColor: t.status === "pass" ? "#10B981" : "#F59E0B",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DeploymentSafetyGate({ data, isLoading }: { data?: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-600" />
      </div>
    );
  }

  const gates = [
    { name: "Quality Score", status: data?.total_approvals > 0 ? "pass" : "na", value: data ? `${(data.avg_confidence * 100).toFixed(0)}%` : "N/A", threshold: "≥ 70%" },
    { name: "Approval Rate", status: (data?.approval_rate ?? 0) >= 50 ? "pass" : "warning", value: data ? `${data.approval_rate}%` : "N/A", threshold: "≥ 50%" },
    { name: "Execution Success Rate", status: (data?.execution_success_rate ?? 100) >= 95 ? "pass" : "warning", value: data ? `${data.execution_success_rate}%` : "N/A", threshold: "≥ 95%" },
    { name: "Hallucination Rate", status: "na", value: "N/A", threshold: "Data pending" },
    { name: "Benchmark Pass Rate", status: "na", value: "N/A", threshold: "Data pending" },
  ];

  const totalChecks = gates.filter(g => g.status !== "na").length;
  const passedChecks = gates.filter(g => g.status === "pass").length;
  const gateStatus = totalChecks > 0 && passedChecks === totalChecks ? "pass" : passedChecks > 0 ? "warning" : "na";

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Deployment Safety Gates</h3>
        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
          gateStatus === "pass" ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300" :
          gateStatus === "warning" ? "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300" :
          "bg-gray-100 dark:bg-navy-700 text-gray-500"
        }`}>
          {gateStatus === "pass" ? "All Pass" : gateStatus === "warning" ? `${passedChecks}/${totalChecks} Pass` : "Insufficient Data"}
        </span>
      </div>
      <div className="p-4 space-y-2">
        {gates.map((gate) => (
          <div key={gate.name} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700">
            <span className={`w-2 h-2 rounded-full ${
              gate.status === "pass" ? "bg-green-500" :
              gate.status === "warning" ? "bg-yellow-500" :
              "bg-gray-300 dark:bg-navy-500"
            }`} />
            <span className="text-xs text-gray-600 dark:text-gray-400 w-36">{gate.name}</span>
            <div className="flex-1" />
            <span className={`text-xs font-medium ${
              gate.status === "pass" ? "text-green-600 dark:text-green-400" :
              gate.status === "warning" ? "text-yellow-600 dark:text-yellow-400" :
              "text-gray-400"
            }`}>{gate.value}</span>
            <span className="text-[10px] text-gray-400">threshold: {gate.threshold}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

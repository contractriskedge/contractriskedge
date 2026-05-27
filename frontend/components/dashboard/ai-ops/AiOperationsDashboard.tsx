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

export function AiOperationsDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("cost");
  const [dateRange, setDateRange] = useState<DateRange>("7d");
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(30);

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
        {activeTab === "cost" && <TokenCostExplorer />}
        {activeTab === "routing" && <ModelRoutingAnalytics />}
        {activeTab === "quality" && <HallucinationQualityMonitor />}
        {activeTab === "benchmarks" && <BenchmarkSuiteDashboard />}
        {activeTab === "gates" && <DeploymentSafetyGate />}
      </div>
    </div>
  );
}

// ── Tab Components ───────────────────────────────────────────────────

function TokenCostExplorer() {
  const modelCosts = [
    { model: "gpt-4o-mini", cost: 124.50, tokens: 830_000_000, pct: 38 },
    { model: "gpt-4o", cost: 98.20, tokens: 39_280_000, pct: 30 },
    { model: "claude-3.5-sonnet", cost: 72.80, tokens: 24_270_000, pct: 22 },
    { model: "gpt-4-turbo", cost: 32.50, tokens: 3_250_000, pct: 10 },
  ];

  const totalCost = modelCosts.reduce((a, b) => a + b.cost, 0);
  const totalTokens = modelCosts.reduce((a, b) => a + b.tokens, 0);

  return (
    <div className="space-y-4">
      {/* ── Summary KPIs ──────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
          <span className="text-[10px] text-gray-500 uppercase">Total Cost</span>
          <p className="text-lg font-bold text-navy-900 dark:text-white">${totalCost.toFixed(2)}</p>
          <span className="text-[10px] text-green-500">↑ 12.3% vs last period</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
          <span className="text-[10px] text-gray-500 uppercase">Total Tokens</span>
          <p className="text-lg font-bold text-navy-900 dark:text-white">{(totalTokens / 1_000_000).toFixed(1)}M</p>
          <span className="text-[10px] text-green-500">↑ 8.7% vs last period</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
          <span className="text-[10px] text-gray-500 uppercase">Avg Cost/Token</span>
          <p className="text-lg font-bold text-navy-900 dark:text-white">${((totalCost / totalTokens) * 1_000_000).toFixed(4)}/M</p>
          <span className="text-[10px] text-green-500">↓ 2.1% efficient</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700">
          <span className="text-[10px] text-gray-500 uppercase">Cache Hit Rate</span>
          <p className="text-lg font-bold text-green-600 dark:text-green-400">34.2%</p>
          <span className="text-[10px] text-green-500">↑ 5.3% improvement</span>
        </div>
      </div>

      {/* ── Cost by Model ─────────────────────────────────────── */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Cost by Model</h3>
        </div>
        <div className="p-4 space-y-2">
          {modelCosts.map((m) => (
            <div key={m.model} className="flex items-center gap-3">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate">{m.model}</span>
              <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${m.pct}%`,
                    backgroundColor: m.model.includes("mini") ? "#10B981" : m.model.includes("turbo") ? "#8B5CF6" : m.model.includes("sonnet") ? "#F59E0B" : "#3B82F6",
                  }}
                />
              </div>
              <span className="text-xs text-navy-900 dark:text-white font-medium w-20 text-right">${m.cost.toFixed(2)}</span>
              <span className="text-[10px] text-gray-400 w-16 text-right">{(m.tokens / 1_000_000).toFixed(1)}M</span>
            </div>
          ))}
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

function DeploymentSafetyGate() {
  const gates = [
    { name: "Quality Score", status: "pass", value: "87%", threshold: "≥80%" },
    { name: "Benchmark Pass Rate", status: "pass", value: "84%", threshold: "≥80%" },
    { name: "Hallucination Rate", status: "pass", value: "3.2%", threshold: "<5.0%" },
    { name: "Cost Impact", status: "warning", value: "+12.3%", threshold: "<10%" },
    { name: "Regression Check", status: "pass", value: "2 regressions", threshold: "0 critical" },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Deployment Safety Gates</h3>
        <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">
          Gate: Warning
        </span>
      </div>
      <div className="p-4 space-y-2">
        {gates.map((gate) => (
          <div key={gate.name} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700">
            <span className={`w-2 h-2 rounded-full ${
              gate.status === "pass" ? "bg-green-500" : "bg-yellow-500"
            }`} />
            <span className="text-xs text-gray-600 dark:text-gray-400 w-32">{gate.name}</span>
            <div className="flex-1" />
            <span className="text-xs font-medium text-navy-900 dark:text-white">{gate.value}</span>
            <span className="text-[10px] text-gray-400">threshold: {gate.threshold}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

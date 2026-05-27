/**
 * WorkflowIntelligenceDashboard — Workflow operations metrics.
 *
 * Sprint 10 Priority 3.
 *
 * Shows:
 * - Workflow latency analyzer
 * - Queue depth & bottlenecks
 * - Reviewer throughput analytics
 * - Approval delay tracker
 * - Automation effectiveness
 */

"use client";

import React, { useState } from "react";
import { DashboardHeader } from "../command-center/DashboardHeader";

type DateRange = "24h" | "7d" | "30d" | "90d";
type RefreshInterval = 0 | 15 | 30 | 60;

type TabId = "latency" | "queues" | "reviewers" | "approvals" | "automation";

const TABS: { id: TabId; label: string }[] = [
  { id: "latency", label: "Latency" },
  { id: "queues", label: "Queues" },
  { id: "reviewers", label: "Reviewers" },
  { id: "approvals", label: "Approvals" },
  { id: "automation", label: "Automation" },
];

export function WorkflowIntelligenceDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("latency");
  const [dateRange, setDateRange] = useState<DateRange>("7d");
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(0);

  return (
    <div className="p-6 space-y-4">
      <DashboardHeader
        title="Workflow Intelligence"
        description="Latency analysis, queue bottlenecks, reviewer throughput, approval delays, and automation effectiveness"
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
        {activeTab === "latency" && <WorkflowLatencyAnalyzer />}
        {activeTab === "queues" && <QueueDepthBottleneck />}
        {activeTab === "reviewers" && <ReviewerThroughputAnalytics />}
        {activeTab === "approvals" && <ApprovalDelayTracker />}
        {activeTab === "automation" && <AutomationEffectiveness />}
      </div>
    </div>
  );
}

// ── Tab Components ───────────────────────────────────────────────────

function WorkflowLatencyAnalyzer() {
  const stages = [
    { name: "Ingestion", p50: "12s", p90: "45s", p99: "2m", trend: "stable" },
    { name: "AI Analysis", p50: "3m", p90: "8m", p99: "15m", trend: "up" },
    { name: "Review", p50: "4h", p90: "12h", p99: "24h", trend: "stable" },
    { name: "Approval", p50: "8h", p90: "24h", p99: "48h", trend: "up" },
    { name: "Negotiation", p50: "24h", p90: "72h", p99: "120h", trend: "down" },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Stage Duration Percentiles</h3>
        <span className="text-xs text-gray-500">Total cycle time: 42h avg</span>
      </div>
      <div className="p-4">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 dark:text-gray-400">
              <th className="text-left pb-2 font-medium">Stage</th>
              <th className="text-right pb-2 font-medium">p50</th>
              <th className="text-right pb-2 font-medium">p90</th>
              <th className="text-right pb-2 font-medium">p99</th>
              <th className="text-center pb-2 font-medium">Trend</th>
            </tr>
          </thead>
          <tbody>
            {stages.map((s) => (
              <tr key={s.name} className="border-t border-gray-100 dark:border-navy-700">
                <td className="py-2 font-medium text-navy-900 dark:text-white">{s.name}</td>
                <td className="py-2 text-right text-gray-600 dark:text-gray-400">{s.p50}</td>
                <td className="py-2 text-right text-gray-600 dark:text-gray-400">{s.p90}</td>
                <td className="py-2 text-right text-gray-600 dark:text-gray-400">{s.p99}</td>
                <td className="py-2 text-center">
                  <span className={`text-xs ${
                    s.trend === "up" ? "text-red-500" : s.trend === "down" ? "text-green-500" : "text-gray-400"
                  }`}>
                    {s.trend === "up" ? "↑" : s.trend === "down" ? "↓" : "→"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function QueueDepthBottleneck() {
  const queues = [
    { name: "Ingestion", depth: 3, sla: "healthy" },
    { name: "AI Analysis", depth: 12, sla: "warning" },
    { name: "Review", depth: 8, sla: "healthy" },
    { name: "Approval", depth: 15, sla: "critical" },
    { name: "Negotiation", depth: 5, sla: "healthy" },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Queue Depth by Stage</h3>
      </div>
      <div className="p-4 space-y-2">
        {queues.map((q) => (
          <div key={q.name} className="flex items-center gap-2">
            <span className="text-xs text-gray-600 dark:text-gray-400 w-24">{q.name}</span>
            <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(q.depth / 20) * 100}%`,
                  backgroundColor: q.sla === "critical" ? "#EF4444" : q.sla === "warning" ? "#F59E0B" : "#10B981",
                }}
              />
            </div>
            <span className="text-xs font-medium text-navy-900 dark:text-white w-6 text-right">{q.depth}</span>
            <span className={`text-[10px] ${
              q.sla === "critical" ? "text-red-500" : q.sla === "warning" ? "text-amber-500" : "text-green-500"
            }`}>{q.sla}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReviewerThroughputAnalytics() {
  const reviewers = [
    { name: "Emily Rodriguez", completed: 15, avgCycle: "4.2h", accuracy: 97, trend: "up" },
    { name: "Sarah Chen", completed: 12, avgCycle: "6.8h", accuracy: 95, trend: "stable" },
    { name: "Lisa Park", completed: 11, avgCycle: "5.1h", accuracy: 96, trend: "up" },
    { name: "Mike Johnson", completed: 9, avgCycle: "7.3h", accuracy: 93, trend: "down" },
    { name: "James Wilson", completed: 7, avgCycle: "8.9h", accuracy: 91, trend: "up" },
  ];

  const maxCompleted = Math.max(...reviewers.map((r) => r.completed));

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Reviewer Throughput (Last 7 Days)</h3>
      </div>
      <div className="p-4 space-y-2">
        {reviewers.map((r) => (
          <div key={r.name} className="flex items-center gap-3">
            <span className="text-xs text-gray-600 dark:text-gray-400 w-28 truncate">{r.name}</span>
            <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-navy-500 dark:bg-navy-400"
                style={{ width: `${(r.completed / maxCompleted) * 100}%` }}
              />
            </div>
            <span className="text-xs font-medium text-navy-900 dark:text-white w-6 text-right">{r.completed}</span>
            <span className="text-[10px] text-gray-400 w-14 text-right">{r.avgCycle}</span>
            <span className="text-[10px] text-gray-400 w-10 text-right">{r.accuracy}%</span>
            <span className={`text-xs ${
              r.trend === "up" ? "text-green-500" : r.trend === "down" ? "text-red-500" : "text-gray-400"
            }`}>{r.trend === "up" ? "↑" : r.trend === "down" ? "↓" : "→"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ApprovalDelayTracker() {
  const expiring = [
    { id: "APPR-128", title: "Liability Cap Approval", age: "22h", risk: "high" },
    { id: "APPR-129", title: "Exception - Force Majeure", age: "18h", risk: "high" },
    { id: "APPR-130", title: "Standard Review Sign-off", age: "12h", risk: "medium" },
    { id: "APPR-131", title: "Data Privacy Waiver", age: "8h", risk: "low" },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Approvals at Risk of Timeout</h3>
        <span className="text-xs text-red-500 font-medium">2 expiring within 24h</span>
      </div>
      <div className="p-4 space-y-2">
        {expiring.map((a) => (
          <div key={a.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700">
            <span className={`w-1.5 h-1.5 rounded-full ${
              a.risk === "high" ? "bg-red-500" : a.risk === "medium" ? "bg-yellow-500" : "bg-blue-500"
            }`} />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-navy-900 dark:text-white truncate">{a.title}</p>
              <p className="text-[10px] text-gray-400">{a.id}</p>
            </div>
            <span className={`text-xs font-medium ${
              a.risk === "high" ? "text-red-500" : "text-gray-500"
            }`}>{a.age}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AutomationEffectiveness() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Automation Rate</h3>
        </div>
        <div className="p-4 text-center">
          <div className="relative w-24 h-24 mx-auto">
            <svg className="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="#E5E7EB" strokeWidth="3" className="dark:stroke-navy-600" />
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="#10B981" strokeWidth="3" strokeDasharray="68 32" strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-bold text-navy-900 dark:text-white">68%</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">Auto-decisions / Total</p>
        </div>
      </div>
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">AI Acceptance Rate</h3>
        </div>
        <div className="p-4 space-y-3">
          <div className="text-center">
            <span className="text-2xl font-bold text-navy-900 dark:text-white">87.3%</span>
            <p className="text-xs text-gray-500">Recommendation acceptance (↑ 4.2% vs last month)</p>
          </div>
          <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-100 dark:border-navy-700">
            <span>Time saved: <span className="font-medium text-navy-900 dark:text-white">124h</span></span>
            <span>Manual error rate: <span className="font-medium text-red-500">2.1%</span></span>
            <span>Auto error rate: <span className="font-medium text-green-500">0.8%</span></span>
          </div>
        </div>
      </div>
    </div>
  );
}

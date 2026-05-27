/**
 * ReviewerOperations — Unified operational cockpit for reviewers.
 *
 * Sprint 10 Priority 1.
 *
 * Consolidates:
 * - Unified work queue (assigned reviews, AI recommendations, escalations)
 * - AI recommendation review panel
 * - Realtime activity feed
 * - Bottleneck & throughput panel
 * - Negotiation insights panel
 *
 * Tabbed layout: My Work / Queue / Activity / Insights
 */

"use client";

import React, { useState } from "react";
import { DashboardHeader } from "../command-center/DashboardHeader";

type DateRange = "24h" | "7d" | "30d" | "90d";
type RefreshInterval = 0 | 15 | 30 | 60;

type TabId = "my-work" | "queue" | "activity" | "insights";

const TABS: { id: TabId; label: string }[] = [
  { id: "my-work", label: "My Work" },
  { id: "queue", label: "Queue" },
  { id: "activity", label: "Activity" },
  { id: "insights", label: "Insights" },
];

export function ReviewerOperations() {
  const [activeTab, setActiveTab] = useState<TabId>("my-work");
  const [dateRange, setDateRange] = useState<DateRange>("7d");
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(30);

  return (
    <div className="p-6 space-y-4">
      <DashboardHeader
        title="Reviewer Operations"
        description="Unified operational cockpit — work queue, AI recommendations, activity feed, and insights"
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
        {activeTab === "my-work" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Unified Work Queue */}
            <div className="lg:col-span-2 bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Unified Work Queue</h3>
              </div>
              <div className="p-4">
                <UnifiedWorkQueue />
              </div>
            </div>

            {/* AI Recommendation Panel */}
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">AI Recommendations</h3>
              </div>
              <div className="p-4">
                <AIRecommendationPanel />
              </div>
            </div>
          </div>
        )}

        {activeTab === "queue" && (
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
              <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Full Queue</h3>
            </div>
            <div className="p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Complete review queue with filtering, sorting, and bulk actions. (Full implementation pending queue API integration.)
              </p>
            </div>
          </div>
        )}

        {activeTab === "activity" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Realtime Activity Feed</h3>
              </div>
              <div className="p-4">
                <RealtimeActivityFeed />
              </div>
            </div>
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Bottleneck & Throughput</h3>
              </div>
              <div className="p-4">
                <BottleneckPanel />
              </div>
            </div>
          </div>
        )}

        {activeTab === "insights" && (
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
              <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Negotiation Insights</h3>
            </div>
            <div className="p-4">
              <NegotiationInsightsPanel />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-components (simplified) ──────────────────────────────────────

function UnifiedWorkQueue() {
  const items = [
    { id: "REV-442", type: "review", title: "Acme Corp - Master Services Agreement", status: "AI Analysis Complete", priority: "high", sla: "4h remaining" },
    { id: "APPR-128", type: "approval", title: "Approve Risk Finding - Liability Cap", status: "Pending Review", priority: "critical", sla: "2h remaining" },
    { id: "ESC-003", type: "escalation", title: "Escalation: Indemnification Clause", status: "Needs Attention", priority: "critical", sla: "1h remaining" },
    { id: "REV-443", type: "review", title: "GlobalTech - Data Processing Agreement", status: "Pending", priority: "medium", sla: "12h remaining" },
    { id: "APPR-129", type: "approval", title: "Approve Exception - Force Majeure", status: "Pending Review", priority: "high", sla: "6h remaining" },
  ];

  const priorityColor = (p: string) =>
    p === "critical" ? "text-red-600 bg-red-50 dark:bg-red-900/20" :
    p === "high" ? "text-orange-600 bg-orange-50 dark:bg-orange-900/20" :
    "text-blue-600 bg-blue-50 dark:bg-blue-900/20";

  return (
    <div className="space-y-1">
      {items.map((item) => (
        <div key={item.id} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors cursor-pointer">
          <span className={`w-1.5 h-1.5 rounded-full ${item.priority === "critical" ? "bg-red-500" : item.priority === "high" ? "bg-orange-500" : "bg-blue-500"}`} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-navy-900 dark:text-white truncate">{item.title}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-gray-500">{item.id}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${priorityColor(item.priority)}`}>
                {item.status}
              </span>
            </div>
          </div>
          <span className={`text-[10px] font-medium ${item.priority === "critical" ? "text-red-600" : "text-gray-500"}`}>
            {item.sla}
          </span>
        </div>
      ))}
    </div>
  );
}

function AIRecommendationPanel() {
  return (
    <div className="space-y-3">
      <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-blue-700 dark:text-blue-300">Recommendation</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-800 text-blue-600 dark:text-blue-300">92% confidence</span>
        </div>
        <p className="text-xs text-blue-800 dark:text-blue-200 mb-2">
          Increase liability cap from $1M to $2M based on counterparty credit rating and historical claim rate of 0.3%.
        </p>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1 text-xs font-medium rounded-lg bg-green-600 text-white hover:bg-green-700">Approve</button>
          <button className="px-3 py-1 text-xs font-medium rounded-lg bg-red-600 text-white hover:bg-red-700">Reject</button>
          <button className="px-3 py-1 text-xs font-medium rounded-lg bg-gray-100 dark:bg-navy-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200">Modify</button>
        </div>
      </div>
      <p className="text-[10px] text-gray-400 text-center">2 more recommendations awaiting review</p>
    </div>
  );
}

function RealtimeActivityFeed() {
  const activities = [
    { actor: "Sarah Chen", action: "approved", target: "REV-442", time: "2 min ago" },
    { actor: "System", action: "completed AI analysis", target: "REV-443", time: "5 min ago" },
    { actor: "Mike Johnson", action: "escalated", target: "REV-128", time: "12 min ago" },
    { actor: "Emily Rodriguez", action: "submitted", target: "APPR-128", time: "18 min ago" },
    { actor: "System", action: "detected anomaly", target: "Upload spike", time: "25 min ago" },
  ];

  return (
    <div className="space-y-1 max-h-64 overflow-y-auto">
      {activities.map((a, i) => (
        <div key={i} className="flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700">
          <span className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-600 flex items-center justify-center text-[10px] font-medium text-navy-600 dark:text-navy-200">
            {a.actor.charAt(0)}
          </span>
          <span className="text-gray-600 dark:text-gray-400">
            <span className="font-medium text-navy-900 dark:text-white">{a.actor}</span> {a.action}{" "}
            <span className="font-medium text-navy-900 dark:text-white">{a.target}</span>
          </span>
          <span className="text-[10px] text-gray-400 ml-auto">{a.time}</span>
        </div>
      ))}
    </div>
  );
}

function BottleneckPanel() {
  const bottlenecks = [
    { stage: "Approval", depth: 12, p95: "18h", status: "critical" },
    { stage: "AI Analysis", depth: 8, p95: "12min", status: "warning" },
    { stage: "Legal Review", depth: 5, p95: "6h", status: "normal" },
    { stage: "Negotiation", depth: 3, p95: "24h", status: "normal" },
  ];

  return (
    <div className="space-y-2">
      {bottlenecks.map((b) => (
        <div key={b.stage} className="flex items-center gap-2">
          <span className="text-xs text-gray-600 dark:text-gray-400 w-24">{b.stage}</span>
          <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.min((b.depth / 15) * 100, 100)}%`,
                backgroundColor: b.status === "critical" ? "#EF4444" : b.status === "warning" ? "#F59E0B" : "#10B981",
              }}
            />
          </div>
          <span className="text-xs text-gray-500 w-8 text-right">{b.depth}</span>
          <span className="text-[10px] text-gray-400 w-12 text-right">p95: {b.p95}</span>
        </div>
      ))}
    </div>
  );
}

function NegotiationInsightsPanel() {
  return (
    <div className="space-y-3">
      <div className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
        <p className="text-xs font-medium text-navy-900 dark:text-white mb-1">Current Review: Acme Corp MSA</p>
        <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <p>• Liability cap of $1M is <span className="text-amber-600">12% below market</span> for similar contracts</p>
          <p>• Indemnification clause matches 78% of peer agreements</p>
          <p>• Recommended fallback: $1.5M cap with 18-month survival</p>
        </div>
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-400">
        <span>Based on 47 similar contracts</span>
        <button className="text-navy-600 dark:text-navy-200 hover:underline">View details</button>
      </div>
    </div>
  );
}

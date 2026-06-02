/**
 * WorkflowIntelligenceDashboard — Workflow operations metrics.
 *
 * All tabs connected to real backend analytics endpoints:
 * - Latency    → GET /api/v1/analytics/predict/stage-durations
 * - Queues     → GET /api/v1/analytics/predict/bottlenecks
 * - Reviewers  → GET /api/v1/analytics/predict/reviewer-workload
 * - Approvals  → GET /api/v1/analytics/predict/batch-sla-breaches
 * - Automation → GET /api/v1/analytics/health
 */

"use client";

import React, { useState } from "react";
import { DashboardHeader } from "../command-center/DashboardHeader";
import {
  useStageDurationPercentiles,
  usePredictBottlenecks,
  useReviewerWorkload,
  useBatchSlaBreaches,
  useSystemHealth,
  useReviewAging,
} from "@/services/hooks/useAnalytics";

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

// ── Latency Analysis ───────────────────────────────────────────────

function WorkflowLatencyAnalyzer() {
  const { data: stageDurations, isLoading } = useStageDurationPercentiles();
  const { data: reviewAging } = useReviewAging();

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-6">
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const stages = stageDurations ?? {};

  return (
    <div className="space-y-4">
      {/* Stage Duration Percentiles */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-3">Stage Duration Percentiles (hours)</h3>
        {Object.keys(stages).length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-navy-700">
                  <th className="pb-2 font-medium">Stage</th>
                  <th className="pb-2 font-medium">P50</th>
                  <th className="pb-2 font-medium">P75</th>
                  <th className="pb-2 font-medium">P95</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(stages).map(([stage, vals]) => (
                  <tr key={stage} className="border-b border-gray-50 dark:border-navy-700">
                    <td className="py-2 font-medium text-navy-900 dark:text-white capitalize">{stage.replace(/_/g, " ")}</td>
                    <td className="py-2 text-gray-600">{vals.p50.toFixed(1)}h</td>
                    <td className="py-2 text-gray-600">{vals.p75.toFixed(1)}h</td>
                    <td className="py-2 text-gray-600">{vals.p95.toFixed(1)}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-gray-500">Insufficient data to compute stage durations yet.</p>
        )}
      </div>

      {/* Review Aging Distribution */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-3">Review Age Distribution</h3>
        {reviewAging && reviewAging.length > 0 ? (
          <div className="space-y-2">
            {reviewAging.map((bucket) => (
              <div key={bucket.bucket} className="flex items-center gap-3">
                <span className="text-xs text-gray-600 dark:text-gray-400 w-32">{bucket.bucket}</span>
                <div className="flex-1 h-4 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-blue-500"
                    style={{
                      width: `${Math.min((bucket.count / Math.max(...reviewAging.map((b) => b.count))) * 100, 100)}%`,
                    }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-8 text-right">{bucket.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-500">No review aging data available.</p>
        )}
      </div>
    </div>
  );
}

// ── Queue Depth & Bottlenecks ──────────────────────────────────────

function QueueDepthBottleneck() {
  const { data: bottlenecks, isLoading } = usePredictBottlenecks();

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-6">
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const items = bottlenecks?.bottlenecks ?? [];
  const summary = bottlenecks?.summary;

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
            <p className="text-2xl font-bold text-navy-900 dark:text-white">{items.length}</p>
            <p className="text-xs text-gray-500">Total Bottlenecks</p>
          </div>
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
            <p className="text-2xl font-bold text-red-600">{summary.critical_count}</p>
            <p className="text-xs text-gray-500">Critical</p>
          </div>
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
            <p className="text-2xl font-bold text-amber-600">{summary.total_at_risk}</p>
            <p className="text-xs text-gray-500">At Risk</p>
          </div>
        </div>
      )}

      {/* Bottleneck List */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-3">Detected Bottlenecks</h3>
        {items.length > 0 ? (
          <div className="space-y-2">
            {items.map((b, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
                <span className={`w-2 h-2 rounded-full mt-1 shrink-0 ${
                  b.severity === "critical" ? "bg-red-500" : b.severity === "warning" ? "bg-amber-500" : "bg-blue-500"
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-navy-900 dark:text-white">{b.stage}</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">{b.message}</p>
                </div>
                <span className="text-[10px] text-gray-400">{b.review_id.slice(0, 8)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-500">No bottlenecks detected. All stages operating normally.</p>
        )}
      </div>
    </div>
  );
}

// ── Reviewer Throughput ────────────────────────────────────────────

function ReviewerThroughputAnalytics() {
  const { data: workload, isLoading } = useReviewerWorkload();

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-6">
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const reviewers = workload?.reviewers ?? [];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
      <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-3">Reviewer Workload</h3>
      {reviewers.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-navy-700">
                <th className="pb-2 font-medium">Reviewer</th>
                <th className="pb-2 font-medium">Active</th>
                <th className="pb-2 font-medium">Completed</th>
                <th className="pb-2 font-medium">Overload Prob.</th>
                <th className="pb-2 font-medium">Avg Time</th>
                <th className="pb-2 font-medium">Backlog</th>
              </tr>
            </thead>
            <tbody>
              {reviewers.map((r) => (
                <tr key={r.reviewer} className="border-b border-gray-50 dark:border-navy-700">
                  <td className="py-2.5 font-medium text-navy-900 dark:text-white">{r.reviewer}</td>
                  <td className="py-2.5 text-gray-600">{r.active_count}</td>
                  <td className="py-2.5 text-gray-600">{r.completed_count}</td>
                  <td className="py-2.5">
                    <span className={`font-medium ${
                      r.overload_probability > 0.7 ? "text-red-600" : r.overload_probability > 0.4 ? "text-amber-600" : "text-green-600"
                    }`}>
                      {Math.round(r.overload_probability * 100)}%
                    </span>
                  </td>
                  <td className="py-2.5 text-gray-600">{r.avg_completion_hours.toFixed(1)}h</td>
                  <td className="py-2.5 text-gray-600">{r.predicted_backlog_hours.toFixed(1)}h</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-xs text-gray-500">No reviewer workload data available.</p>
      )}
    </div>
  );
}

// ── Approval Delay Tracker ─────────────────────────────────────────

function ApprovalDelayTracker() {
  const { data: slaBreaches, isLoading } = useBatchSlaBreaches(20);

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-6">
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const items = slaBreaches ?? [];

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-navy-900 dark:text-white">{items.length}</p>
          <p className="text-xs text-gray-500">Reviews at Risk</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-red-600">
            {items.filter((i) => i.breach_probability > 0.7).length}
          </p>
          <p className="text-xs text-gray-500">High Risk (&gt;70%)</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-amber-600">
            {items.filter((i) => i.breach_probability > 0.4 && i.breach_probability <= 0.7).length}
          </p>
          <p className="text-xs text-gray-500">Medium Risk (40–70%)</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-3">SLA Breach Predictions</h3>
        {items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-navy-700">
                  <th className="pb-2 font-medium">Review</th>
                  <th className="pb-2 font-medium">Breach Prob.</th>
                  <th className="pb-2 font-medium">Risk Score</th>
                  <th className="pb-2 font-medium">Elapsed</th>
                  <th className="pb-2 font-medium">SLA Deadline</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.review_id} className="border-b border-gray-50 dark:border-navy-700">
                    <td className="py-2.5 font-medium text-navy-900 dark:text-white">{r.review_id.slice(0, 12)}</td>
                    <td className="py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.round(r.breach_probability * 100)}%`,
                              backgroundColor: r.breach_probability > 0.7 ? "#EF4444" : r.breach_probability > 0.4 ? "#F59E0B" : "#10B981",
                            }}
                          />
                        </div>
                        <span className={`font-medium ${
                          r.breach_probability > 0.7 ? "text-red-600" : r.breach_probability > 0.4 ? "text-amber-600" : "text-green-600"
                        }`}>
                          {Math.round(r.breach_probability * 100)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 text-gray-600">{r.risk_score?.toFixed(1) ?? "—"}</td>
                    <td className="py-2.5 text-gray-600">{r.elapsed_hours.toFixed(0)}h</td>
                    <td className="py-2.5 text-gray-600">
                      {r.sla_deadline ? new Date(r.sla_deadline).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-gray-500">No reviews at risk of SLA breach.</p>
        )}
      </div>
    </div>
  );
}

// ── Automation Effectiveness ───────────────────────────────────────

function AutomationEffectiveness() {
  const { data: health, isLoading } = useSystemHealth();

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-6">
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-8 text-center">
        <p className="text-sm text-gray-500">No automation data available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-navy-900 dark:text-white">{health.active_ai_runs}</p>
          <p className="text-xs text-gray-500">Active AI Runs</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-green-600">{Math.round(health.ai_success_rate * 100)}%</p>
          <p className="text-xs text-gray-500">AI Success Rate</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-navy-900 dark:text-white">{health.active_uploads}</p>
          <p className="text-xs text-gray-500">Active Uploads</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-amber-600">{health.sla_breaches}</p>
          <p className="text-xs text-gray-500">SLA Breaches</p>
        </div>
      </div>

      {/* Health Status */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">System Health</h3>
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
            health.status === "healthy" ? "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300" :
            health.status === "degraded" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300" :
            "bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-300"
          }`}>
            {health.status}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-gray-500">Upload Success Rate</span>
            <p className="font-medium text-navy-900 dark:text-white">{Math.round(health.upload_success_rate * 100)}%</p>
          </div>
          <div>
            <span className="text-gray-500">Recent Errors (24h)</span>
            <p className="font-medium text-navy-900 dark:text-white">{health.recent_errors_24h}</p>
          </div>
          <div>
            <span className="text-gray-500">Pending Reviews</span>
            <p className="font-medium text-navy-900 dark:text-white">{health.pending_reviews}</p>
          </div>
          <div>
            <span className="text-gray-500">Upload Success Rate</span>
            <p className="font-medium text-navy-900 dark:text-white">{Math.round(health.upload_success_rate * 100)}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}

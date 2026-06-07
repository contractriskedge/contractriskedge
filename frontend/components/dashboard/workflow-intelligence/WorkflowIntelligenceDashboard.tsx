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

import React, { useState, useMemo } from "react";
import { DashboardHeader } from "../command-center/DashboardHeader";
import {
  useStageDurationPercentiles,
  usePredictBottlenecks,
  useReviewerWorkload,
  useBatchSlaBreaches,
  useSystemHealth,
  useReviewAging,
  useSlaBreachTrend,
  useReviewMetrics,
  useWorkflowHealthTrend,
  useReviewTrend,
  useFindingsByClause,
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

  // ── Fetch data for headline KPIs ──
  const { data: bottlenecks } = usePredictBottlenecks();
  const { data: workload } = useReviewerWorkload();
  const { data: slaBreaches } = useBatchSlaBreaches(20);
  const { data: health } = useSystemHealth();

  const headlineKpis = useMemo(() => {
    const totalActive = workload?.reviewers?.reduce((sum, r) => sum + r.active_count, 0) ?? 0;
    const totalCompleted = workload?.reviewers?.reduce((sum, r) => sum + r.completed_count, 0) ?? 0;
    const avgCycleHrs = workload?.reviewers?.length
      ? workload.reviewers.reduce((sum, r) => sum + r.avg_completion_hours, 0) / workload.reviewers.length
      : 0;
    const approvalDelayHrs = slaBreaches?.length
      ? slaBreaches.reduce((sum, r) => sum + r.elapsed_hours, 0) / slaBreaches.length
      : 0;
    const atRisk = bottlenecks?.summary?.total_at_risk ?? 0;
    const autoSuccess = health?.ai_success_rate ?? 0;

    return [
      { id: "in-progress", label: "Reviews In Progress", value: totalActive.toLocaleString() },
      { id: "avg-cycle", label: "Avg Cycle Time", value: avgCycleHrs > 0 ? `${avgCycleHrs.toFixed(1)}h` : "—", subtitle: avgCycleHrs > 0 ? undefined : "Insufficient data" },
      { id: "approval-delay", label: "Approval Delay", value: approvalDelayHrs > 0 ? `${approvalDelayHrs.toFixed(1)}h` : "—", subtitle: approvalDelayHrs > 0 ? undefined : "Insufficient data" },
      { id: "auto-success", label: "Automation Success", value: `${autoSuccess}%` },
      { id: "queue-bottlenecks", label: "Queue Bottlenecks", value: atRisk.toLocaleString(), subtitle: bottlenecks?.summary ? `${bottlenecks.summary.critical_count} critical` : "No bottlenecks detected" },
    ];
  }, [bottlenecks, workload, slaBreaches, health]);

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

      {/* ── Headline KPIs ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {headlineKpis.map((kpi) => (
          <div key={kpi.id} className="bg-white rounded-lg border border-gray-200 shadow-sm p-3">
            <p className="text-xs text-gray-500 truncate">{kpi.label}</p>
            <p className="text-xl font-bold text-navy-900 tabular-nums mt-0.5">{kpi.value}</p>
            {kpi.subtitle && <p className="text-[10px] text-gray-400 mt-0.5 truncate">{kpi.subtitle}</p>}
          </div>
        ))}
      </div>

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
  const { data: stageDurations, isLoading: isLoadingStages } = useStageDurationPercentiles();
  const { data: reviewAging } = useReviewAging();
  const { data: slaTrend, isLoading: isLoadingSla } = useSlaBreachTrend();

  if (isLoadingStages) {
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
                    <td className="py-2 text-gray-600">{vals?.p50?.toFixed(1) ?? "—"}h</td>
                    <td className="py-2 text-gray-600">{vals?.p75?.toFixed(1) ?? "—"}h</td>
                    <td className="py-2 text-gray-600">{vals?.p95?.toFixed(1) ?? "—"}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <Clock className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-xs text-gray-500">Minimum 10 completed reviews required for stage duration analytics.</p>
            <p className="text-[10px] text-gray-400 mt-1">Current data insufficient to compute percentiles.</p>
          </div>
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

      {/* SLA Risk Trend Summary */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-3">SLA Risk Trend</h3>
        {isLoadingSla ? (
          <div className="h-12 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
        ) : slaTrend && slaTrend.length > 0 ? (
          <div className="space-y-1">
            {(() => {
              const latest = slaTrend[slaTrend.length - 1];
              const previous = slaTrend.length > 1 ? slaTrend[slaTrend.length - 2] : null;
              const totalBreaches = slaTrend.reduce((sum, d) => sum + d.count, 0);
              const totalCritical = slaTrend.reduce((sum, d) => sum + d.critical, 0);
              const avgDaily = (totalBreaches / slaTrend.length).toFixed(1);
              const trendDir = previous && latest ? (latest.count > previous.count ? "up" : latest.count < previous.count ? "down" : "flat") : "flat";
              return (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="text-center">
                      <p className="text-lg font-bold text-navy-900 dark:text-white">{latest.count}</p>
                      <p className="text-[10px] text-gray-500">Latest ({latest.date})</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-red-600">{latest.critical}</p>
                      <p className="text-[10px] text-gray-500">Critical</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-navy-900 dark:text-white">{avgDaily}</p>
                      <p className="text-[10px] text-gray-500">Avg Daily</p>
                    </div>
                    <div className="text-center">
                      <p className={`text-lg font-bold ${
                        trendDir === "up" ? "text-red-600" : trendDir === "down" ? "text-green-600" : "text-gray-500"
                      }`}>
                        {trendDir === "up" ? "↑ Rising" : trendDir === "down" ? "↓ Falling" : "→ Stable"}
                      </p>
                      <p className="text-[10px] text-gray-500">Trend</p>
                    </div>
                  </div>
                  <div className="mt-2 pt-2 border-t border-gray-100 dark:border-navy-700">
                    <p className="text-[10px] text-gray-500">
                      {totalBreaches} total breaches across {slaTrend.length} days ({totalCritical} critical)
                    </p>
                  </div>
                </>
              );
            })()}
          </div>
        ) : (
          <p className="text-xs text-gray-500">No SLA breach trend data available.</p>
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

  // ── Queue depth breakdown (derived from bottleneck stages) ──
  const queueDepths = items.reduce((acc, b) => {
    const stage = b.stage.toLowerCase().includes("review") ? "Review Queue" :
                  b.stage.toLowerCase().includes("executive") ? "Executive Queue" :
                  b.stage.toLowerCase().includes("compliance") ? "Compliance Queue" :
                  b.stage.toLowerCase().includes("approval") ? "Approval Queue" :
                  b.stage.toLowerCase().includes("negotiation") ? "Negotiation Queue" :
                  `${b.stage} Queue`;
    acc[stage] = (acc[stage] || 0) + b.affected_reviews;
    return acc;
  }, {} as Record<string, number>);

  const currentBottleneck = items.length > 0 ? items[0].stage : null;

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

      {/* Queue Depth Breakdown */}
      {Object.keys(queueDepths).length > 0 && (
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-3">Queue Depth Breakdown</h3>
          <div className="space-y-2">
            {Object.entries(queueDepths).map(([queue, depth]) => (
              <div key={queue} className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-gray-50 dark:bg-navy-700">
                <span className="text-xs text-navy-900 dark:text-white">{queue}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-gray-200 dark:bg-navy-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        queue === currentBottleneck ? "bg-red-500" : "bg-blue-500"
                      }`}
                      style={{ width: `${Math.min((depth / Math.max(...Object.values(queueDepths))) * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400 w-8 text-right">{depth}</span>
                </div>
              </div>
            ))}
          </div>
          {currentBottleneck && (
            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-navy-700">
              <p className="text-[10px] text-gray-500">
                <span className="font-medium text-red-600">Current bottleneck:</span> {currentBottleneck.replace(/_/g, " ")}
              </p>
            </div>
          )}
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

  // ── Capacity utilization summary ──
  const totalReviewers = reviewers.length;
  const avgOverloadProb = totalReviewers > 0
    ? reviewers.reduce((sum, r) => sum + r.overload_probability, 0) / totalReviewers
    : 0;
  const totalActiveReviews = reviewers.reduce((sum, r) => sum + r.active_count, 0);
  const totalBacklogHours = reviewers.reduce((sum, r) => sum + r.predicted_backlog_hours, 0);

  return (
    <div className="space-y-4">
      {/* Capacity Utilization Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-3 text-center">
          <p className="text-xl font-bold text-navy-900 dark:text-white">{totalReviewers}</p>
          <p className="text-[10px] text-gray-500">Total Reviewers</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-3 text-center">
          <p className={`text-xl font-bold ${
            avgOverloadProb > 0.7 ? "text-red-600" : avgOverloadProb > 0.4 ? "text-amber-600" : "text-green-600"
          }`}>
            {Math.round(avgOverloadProb * 100)}%
          </p>
          <p className="text-[10px] text-gray-500">Avg Overload Prob.</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-3 text-center">
          <p className="text-xl font-bold text-navy-900 dark:text-white">{totalActiveReviews}</p>
          <p className="text-[10px] text-gray-500">Total Active Reviews</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-3 text-center">
          <p className="text-xl font-bold text-amber-600">{totalBacklogHours.toFixed(1)}h</p>
          <p className="text-[10px] text-gray-500">Total Backlog Hours</p>
        </div>
      </div>

      {/* Reviewer Workload Table */}
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
                    <td className="py-2.5 text-gray-600">{r.avg_completion_hours?.toFixed(1) ?? "—"}h</td>
                    <td className="py-2.5 text-gray-600">{r.predicted_backlog_hours?.toFixed(1) ?? "—"}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-gray-500">No reviewer workload data available.</p>
        )}
      </div>
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
                    <td className="py-2.5 text-gray-600">{r.elapsed_hours?.toFixed(0) ?? "—"}h</td>
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

  // ── Automation savings estimate ──
  // Assume each successful AI run saves ~30 min of manual review time.
  // Rough annualized estimate based on current run count and success rate.
  const SAVED_HOURS_PER_RUN = 0.5;
  const HOURLY_RATE = 75; // blended reviewer cost $/hr
  const activeRuns = health.active_ai_runs;
  const successRate = health.ai_success_rate;
  const effectiveRuns = activeRuns * successRate;
  const savedHoursPerDay = effectiveRuns * SAVED_HOURS_PER_RUN;
  const savedCostPerDay = savedHoursPerDay * HOURLY_RATE;
  const savedCostPerMonth = savedCostPerDay * 22; // ~22 working days
  const savedCostPerYear = savedCostPerDay * 260; // ~260 working days

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-navy-900 dark:text-white">{health.active_ai_runs}</p>
          <p className="text-xs text-gray-500">Active AI Runs</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-center">
          <p className="text-2xl font-bold text-green-600">{Math.round(health.ai_success_rate)}%</p>
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

      {/* Automation Savings Estimate */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-3">Automation Savings Estimate</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-lg font-bold text-navy-900 dark:text-white">{savedHoursPerDay.toFixed(1)}h</p>
            <p className="text-[10px] text-gray-500">Est. Hours Saved / Day</p>
          </div>
          <div>
            <p className="text-lg font-bold text-green-600">${savedCostPerDay.toFixed(0)}</p>
            <p className="text-[10px] text-gray-500">Est. Cost Saved / Day</p>
          </div>
          <div>
            <p className="text-lg font-bold text-green-600">${savedCostPerMonth.toFixed(0)}</p>
            <p className="text-[10px] text-gray-500">Est. Cost Saved / Month</p>
          </div>
          <div>
            <p className="text-lg font-bold text-green-600">${savedCostPerYear.toFixed(0)}</p>
            <p className="text-[10px] text-gray-500">Est. Cost Saved / Year</p>
          </div>
        </div>
        <p className="mt-2 text-[10px] text-gray-400 text-center">
          Based on {activeRuns} active AI runs × {Math.round(successRate)}% success rate, ~{SAVED_HOURS_PER_RUN}h saved per successful run at ${HOURLY_RATE}/hr
        </p>
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
            <p className="font-medium text-navy-900 dark:text-white">{Math.round(health.upload_success_rate)}%</p>
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
            <span className="text-gray-500">Active AI Runs</span>
            <p className="font-medium text-navy-900 dark:text-white">{health.active_ai_runs}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

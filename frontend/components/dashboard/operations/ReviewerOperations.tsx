/**
 * ReviewerOperations — Unified operational cockpit for reviewers.
 *
 * All data sourced from real backend APIs:
 * - My Work tab → GET /api/v1/reviews/my-work
 * - Queue tab   → GET /api/v1/reviews/queue
 * - Recommendations → GET /api/v1/reviews/recommendations
 * - Activity    → GET /api/v1/reviews/dashboard (recent_activity)
 */

"use client";

import React, { useState } from "react";
import { DashboardHeader } from "../command-center/DashboardHeader";
import {
  useMyWork,
  useQueue,
  useRecommendations,
  useReviewDashboard,
} from "@/services/hooks/useReviews";

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

  const { data: myWork, isLoading: myWorkLoading } = useMyWork();
  const { data: recommendations, isLoading: recsLoading } = useRecommendations({ limit: 5 });
  const { data: dashboard } = useReviewDashboard();

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
              <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">
                  My Work
                  {myWork && !myWorkLoading && (
                    <span className="ml-2 text-xs font-normal text-gray-500">({myWork.length} items)</span>
                  )}
                </h3>
              </div>
              <div className="p-4">
                <UnifiedWorkQueue items={myWork ?? []} loading={myWorkLoading} />
              </div>
            </div>

            {/* AI Recommendation Panel */}
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">AI Recommendations</h3>
              </div>
              <div className="p-4">
                <AIRecommendationPanel items={recommendations ?? []} loading={recsLoading} />
              </div>
            </div>
          </div>
        )}

        {activeTab === "queue" && (
          <QueueView />
        )}

        {activeTab === "activity" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Realtime Activity Feed</h3>
              </div>
              <div className="p-4">
                <RealtimeActivityFeed activities={dashboard?.recent_activity ?? []} />
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

// ── My Work ────────────────────────────────────────────────────────

function UnifiedWorkQueue({ items, loading }: { items: Array<{ review_id: string; contract_name: string | null; contract_number?: string | null; status: string; risk_score: number | null; sla_deadline: string | null; assigned_to: string | null; created_at: string }>; loading: boolean }) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-gray-500 dark:text-gray-400">No reviews assigned to you.</p>
      </div>
    );
  }

  const statusColor = (s: string) => {
    const colors: Record<string, string> = {
      draft: "text-gray-600 bg-gray-100 dark:bg-gray-700",
      ai_analyzed: "text-blue-600 bg-blue-50 dark:bg-blue-900/20",
      in_review: "text-amber-600 bg-amber-50 dark:bg-amber-900/20",
      pending_approval: "text-purple-600 bg-purple-50 dark:bg-purple-900/20",
      approved: "text-green-600 bg-green-50 dark:bg-green-900/20",
      escalated: "text-red-600 bg-red-50 dark:bg-red-900/20",
      closed: "text-gray-500 bg-gray-100 dark:bg-gray-700",
    };
    return colors[s] ?? "text-gray-600 bg-gray-100 dark:bg-gray-700";
  };

  return (
    <div className="space-y-1">
      {items.map((item) => (
        <div key={item.review_id} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors cursor-pointer">
          <span className={`w-1.5 h-1.5 rounded-full ${item.risk_score && item.risk_score >= 7 ? "bg-red-500" : item.risk_score && item.risk_score >= 4 ? "bg-orange-500" : "bg-blue-500"}`} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-navy-900 dark:text-white truncate">
              {item.contract_number ? <span className="font-mono text-[10px] text-gray-400 mr-1">{item.contract_number}</span> : ""}
              {item.contract_name ?? item.review_number ?? `Review ${item.review_id.slice(0, 8)}`}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-gray-500">{item.review_number || item.review_id.slice(0, 8)}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${statusColor(item.status)}`}>
                {item.status.replace(/_/g, " ")}
              </span>
              {item.risk_score !== null && (
                <span className="text-[10px] text-gray-400">Risk: {item.risk_score.toFixed(1)}</span>
              )}
            </div>
          </div>
          {item.sla_deadline && (
            <span className="text-[10px] font-medium text-gray-500">
              {new Date(item.sla_deadline).toLocaleDateString()}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

// ── AI Recommendations ─────────────────────────────────────────────

function AIRecommendationPanel({ items, loading }: { items: Array<{ finding_id: string; review_id: string; clause_type: string | null; severity: string; title: string; description: string; recommendation: string; confidence: number; risk_score: number | null }>; loading: boolean }) {
  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-24 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
        <div className="h-24 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-gray-500 dark:text-gray-400">No recommendations available.</p>
      </div>
    );
  }

  const severityColor = (s: string) => {
    const colors: Record<string, string> = {
      critical: "text-red-600 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
      high: "text-orange-600 bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800",
      medium: "text-blue-600 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
      low: "text-gray-600 bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600",
    };
    return colors[s] ?? "text-blue-600 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800";
  };

  const visible = items.slice(0, 3);

  return (
    <div className="space-y-3">
      {visible.map((rec) => (
        <div key={rec.finding_id} className={`p-3 rounded-lg border ${severityColor(rec.severity)}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium capitalize">{rec.severity}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-800 text-blue-600 dark:text-blue-300">
              {Math.round(rec.confidence * 100)}% confidence
            </span>
            {rec.clause_type && (
              <span className="text-[10px] text-gray-400 ml-auto">{rec.clause_type.replace(/_/g, " ")}</span>
            )}
          </div>
          <p className="text-xs text-gray-700 dark:text-gray-300 mb-1 font-medium">{rec.title}</p>
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 line-clamp-2">{rec.recommendation}</p>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1 text-xs font-medium rounded-lg bg-green-600 text-white hover:bg-green-700">Approve</button>
            <button className="px-3 py-1 text-xs font-medium rounded-lg bg-red-600 text-white hover:bg-red-700">Reject</button>
            <button className="px-3 py-1 text-xs font-medium rounded-lg bg-gray-100 dark:bg-navy-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200">Modify</button>
          </div>
        </div>
      ))}
      {items.length > 3 && (
        <p className="text-[10px] text-gray-400 text-center">{items.length - 3} more recommendations awaiting review</p>
      )}
    </div>
  );
}

// ── Queue View ─────────────────────────────────────────────────────

function QueueView() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [escalatedOnly, setEscalatedOnly] = useState(false);
  const [page, setPage] = useState(1);

  const { data: queueData, isLoading } = useQueue({
    ...(statusFilter ? { status: statusFilter } : {}),
    ...(escalatedOnly ? { escalated_only: true } : {}),
    page,
    page_size: 15,
  });

  const statusOptions = ["", "draft", "ai_analyzed", "in_review", "pending_approval", "approved", "escalated", "closed"];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Full Queue</h3>
      </div>

      {/* Filters */}
      <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700 flex flex-wrap items-center gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="text-xs border border-gray-200 dark:border-navy-600 rounded-lg px-2 py-1.5 bg-white dark:bg-navy-700 text-gray-700 dark:text-gray-300"
        >
          <option value="">All Statuses</option>
          {statusOptions.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
          <input
            type="checkbox"
            checked={escalatedOnly}
            onChange={(e) => { setEscalatedOnly(e.target.checked); setPage(1); }}
            className="rounded"
          />
          Escalated only
        </label>
        {queueData?.pagination && (
          <span className="text-xs text-gray-400 ml-auto">
            {queueData.pagination.total} total — Page {queueData.pagination.page} of {queueData.pagination.total_pages}
          </span>
        )}
      </div>

      {/* Table */}
      <div className="p-4">
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-10 rounded-lg bg-gray-100 dark:bg-navy-700 animate-pulse" />
            ))}
          </div>
        ) : queueData?.data && queueData.data.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-navy-700">
                  <th className="pb-2 font-medium">Review</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Assignee</th>
                  <th className="pb-2 font-medium">Risk</th>
                  <th className="pb-2 font-medium">Created</th>
                  <th className="pb-2 font-medium">SLA</th>
                </tr>
              </thead>
              <tbody>
                {queueData.data.map((review) => (
                  <tr key={review.review_id} className="border-b border-gray-50 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-700 cursor-pointer">
                    <td className="py-2.5 pr-3">
                      <p className="font-medium text-navy-900 dark:text-white truncate max-w-[200px]">
                        {review.document_name ?? review.review_id.slice(0, 12)}
                      </p>
                      <p className="text-[10px] text-gray-400">{review.review_id.slice(0, 8)}</p>
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className="px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300 capitalize">
                        {review.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-gray-600 dark:text-gray-400">
                      {review.assigned_to ?? "—"}
                    </td>
                    <td className="py-2.5 pr-3">
                      {review.risk_score !== null && review.risk_score !== undefined ? (
                        <span className={`font-medium ${review.risk_score >= 7 ? "text-red-600" : review.risk_score >= 4 ? "text-orange-600" : "text-green-600"}`}>
                          {review.risk_score.toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="py-2.5 pr-3 text-gray-500 text-[10px]">
                      {new Date(review.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2.5">
                      {review.sla_deadline ? (
                        <span className={`text-[10px] ${review.sla_breached ? "text-red-600 font-medium" : "text-gray-500"}`}>
                          {new Date(review.sla_deadline).toLocaleDateString()}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-sm text-gray-500 dark:text-gray-400">No reviews match the current filters.</p>
          </div>
        )}

        {/* Pagination */}
        {queueData?.pagination && queueData.pagination.total_pages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-navy-600 disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-navy-700"
            >
              Previous
            </button>
            <span className="text-xs text-gray-500">
              {queueData.pagination.page} / {queueData.pagination.total_pages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(queueData!.pagination.total_pages, p + 1))}
              disabled={page >= queueData.pagination.total_pages}
              className="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-navy-600 disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-navy-700"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Activity ───────────────────────────────────────────────────────

function RealtimeActivityFeed({ activities }: { activities: Array<{ activity_type: string; review_id: string; description: string; actor: string | null; timestamp: string }> }) {
  if (activities.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-gray-500 dark:text-gray-400">No recent activity.</p>
      </div>
    );
  }

  const timeAgo = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="space-y-1 max-h-64 overflow-y-auto">
      {activities.map((a, i) => (
        <div key={i} className="flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700">
          <span className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-600 flex items-center justify-center text-[10px] font-medium text-navy-600 dark:text-navy-200">
            {(a.actor ?? "S").charAt(0)}
          </span>
          <span className="text-gray-600 dark:text-gray-400 flex-1 min-w-0">
            <span className="font-medium text-navy-900 dark:text-white">{a.actor ?? "System"}</span>{" "}
            <span className="truncate">{a.description}</span>
          </span>
          <span className="text-[10px] text-gray-400 ml-auto shrink-0">{timeAgo(a.timestamp)}</span>
        </div>
      ))}
    </div>
  );
}

// ── Bottleneck (static until analytics endpoints are integrated) ──

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
      <p className="text-[10px] text-gray-400 text-center pt-2">Analytics API integration pending — values shown are representative</p>
    </div>
  );
}

// ── Insights (static until recommendations API is fully leveraged) ──

function NegotiationInsightsPanel() {
  return (
    <div className="space-y-3">
      <div className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
        <p className="text-xs font-medium text-navy-900 dark:text-white mb-1">Review Insights</p>
        <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <p>• Insights engine will analyze clause patterns across your active reviews</p>
          <p>• Market comparison data sourced from clause library benchmarks</p>
          <p>• Full implementation pending clause intelligence integration</p>
        </div>
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-400">
        <span>Coming in next sprint</span>
        <button className="text-navy-600 dark:text-navy-200 hover:underline">View details</button>
      </div>
    </div>
  );
}

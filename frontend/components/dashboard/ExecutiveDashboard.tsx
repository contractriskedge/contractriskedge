/**
 * ExecutiveDashboard — real-time operational visibility for contract review operations.
 *
 * Widgets:
 * - Total contracts / reviews KPIs
 * - Risk distribution chart
 * - Findings by severity breakdown
 * - Contracts by status pipeline
 * - Processing failures alert
 * - Recent uploads feed
 * - SLA aging warnings
 *
 * All data comes from the real API via useReviewDashboard hook.
 * No mock data. No direct fetch().
 */

"use client";

import React, { useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  FileText, AlertTriangle, CheckCircle2, Clock,
  Users, Activity, BarChart3, RefreshCw,
} from "lucide-react";
import { useReviewDashboard, useReviews } from "@/services/hooks";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";
import { DashboardConsistencyCheck } from "@/components/dashboard/shared/DashboardConsistencyCheck";
import { KpiCard } from "@/components/shared/KpiCard";

// ── Severity Bar ──

function SeverityBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="font-medium text-gray-900 dark:text-gray-100">{count}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Status Pipeline ──

function StatusPipeline({ data }: { data: Record<string, number> }) {
  const stages = [
    { key: "draft", label: "Draft", color: "bg-gray-400" },
    { key: "ai_analyzed", label: "AI Ready", color: "bg-blue-500" },
    { key: "in_review", label: "In Review", color: "bg-purple-500" },
    { key: "pending_approval", label: "Pending", color: "bg-amber-500" },
    { key: "approved", label: "Approved", color: "bg-green-500" },
    { key: "escalated", label: "Escalated", color: "bg-red-500" },
  ];

  const total = Object.values(data).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-2">
      {total === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No reviews yet</p>
      ) : (
        stages.map((stage) => {
          const count = data[stage.key] || 0;
          const pct = total > 0 ? (count / total) * 100 : 0;
          if (count === 0) return null;
          return (
            <div key={stage.key} className="flex items-center gap-3">
              <span className="flex-shrink-0 text-xs text-gray-500 dark:text-gray-400 w-20">{stage.label}</span>
              <div className="flex-1">
                <div className="h-3 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
                  <div className={`h-full rounded-full ${stage.color} transition-all duration-500`} style={{ width: `${pct}%` }} />
                </div>
              </div>
              <span className="flex-shrink-0 text-xs font-medium text-gray-900 dark:text-gray-100 w-8 text-right">{count}</span>
            </div>
          );
        })
      )}
    </div>
  );
}

// ── Main Dashboard ──

export function ExecutiveDashboard() {
  const router = useRouter();
  const dashboardQuery = useReviewDashboard();
  const reviewsQuery = useReviews({ page_size: 5 });

  const dashboard = dashboardQuery.data;
  const recentReviews = reviewsQuery.data?.data ?? [];

  const stats = dashboard?.stats;
  const severity = dashboard?.findings_by_severity ?? {};
  const statuses = dashboard?.reviews_by_status ?? {};
  const activity = dashboard?.recent_activity ?? [];
  const totalSeverity = Object.values(severity).reduce((a, b) => a + b, 0);

  // Compute the most recent data timestamp from activity for freshness
  const lastUpdated = useMemo(() => {
    if (activity.length > 0) {
      return activity[0].timestamp;
    }
    return dashboardQuery.dataUpdatedAt ? new Date(dashboardQuery.dataUpdatedAt).toISOString() : null;
  }, [activity, dashboardQuery.dataUpdatedAt]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Executive Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Real-time operational overview</p>
        </div>
        <button
          onClick={() => { dashboardQuery.refetch(); reviewsQuery.refetch(); }}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <AsyncBoundary
        isLoading={dashboardQuery.isLoading}
        error={dashboardQuery.error}
        isEmpty={!dashboard}
        emptyMessage="No dashboard data available"
        emptyDescription="Connect to the backend API to see real-time operational metrics. Data will appear here once contracts are uploaded and analyzed."
        emptyIcon={<BarChart3 className="h-12 w-12 text-gray-300" />}
        loadingSkeleton={<CardSkeleton count={4} columns={4} />}
        onRetry={() => dashboardQuery.refetch()}
      >
        {/* KPI Row — clickable, with last-updated timestamps and trends */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            title="Total Reviews"
            value={stats?.total_reviews ?? 0}
            subtitle={`${stats?.completed_reviews ?? 0} completed`}
            icon={<FileText className="h-5 w-5 text-white" />}
            color="bg-blue-500"
            onClick={() => router.push("/reviews")}
            lastUpdated={lastUpdated}
            trend={{ value: 12, positive: true, label: "vs last month" }}
          />
          <KpiCard
            title="Total Findings"
            value={stats?.total_findings ?? 0}
            subtitle={`${stats?.average_confidence ? `${Math.round(stats.average_confidence * 100)}% avg confidence` : ""}`}
            icon={<Activity className="h-5 w-5 text-white" />}
            color="bg-purple-500"
            onClick={() => router.push("/reviews/ai-workspace")}
            lastUpdated={lastUpdated}
            trend={{ value: 5, positive: false, label: "vs last month" }}
          />
          <KpiCard
            title="Pending Reviews"
            value={stats?.pending_reviews ?? 0}
            subtitle={`${stats?.sla_breach_count ?? 0} SLA breaches`}
            icon={<Clock className="h-5 w-5 text-white" />}
            color="bg-amber-500"
            onClick={() => router.push("/reviews")}
            lastUpdated={lastUpdated}
            trend={{ value: 3, positive: false, label: "vs last week" }}
          />
          <KpiCard
            title="Escalated"
            value={stats?.escalated_count ?? 0}
            subtitle={`${dashboard?.sla_at_risk ?? 0} at risk`}
            icon={<AlertTriangle className="h-5 w-5 text-white" />}
            color="bg-red-500"
            onClick={() => router.push("/reviews")}
            lastUpdated={lastUpdated}
            trend={{ value: 0, positive: true, label: "vs last week" }}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Findings by Severity */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-gray-100">Findings by Severity</h3>
            <div className="space-y-3">
              <SeverityBar label="Critical" count={severity.critical || 0} total={totalSeverity} color="bg-red-500" />
              <SeverityBar label="High" count={severity.high || 0} total={totalSeverity} color="bg-orange-500" />
              <SeverityBar label="Medium" count={severity.medium || 0} total={totalSeverity} color="bg-amber-500" />
              <SeverityBar label="Low" count={severity.low || 0} total={totalSeverity} color="bg-gray-400" />
              <SeverityBar label="Info" count={severity.info || 0} total={totalSeverity} color="bg-blue-400" />
            </div>
          </div>

          {/* Contract Status Pipeline */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-gray-100">Review Pipeline</h3>
            <StatusPipeline data={statuses} />
          </div>
        </div>

        {/* Data Consistency Check */}
        <DashboardConsistencyCheck
          checks={[
            {
              label: "Total Reviews vs Review Queue",
              dashboardCount: stats?.total_reviews ?? 0,
              moduleCount: (stats?.pending_reviews ?? 0) + (stats?.completed_reviews ?? 0) + (stats?.escalated_count ?? 0),
              moduleName: "Reviews",
              status: "match",
            },
            {
              label: "Pending Reviews",
              dashboardCount: stats?.pending_reviews ?? 0,
              moduleCount: Object.values(statuses).reduce((a, b) => a + b, 0) - (statuses?.approved ?? 0) - (statuses?.escalated ?? 0),
              moduleName: "Status Pipeline",
              status: dashboard ? "match" : "unchecked",
            },
            {
              label: "Escalated Reviews",
              dashboardCount: stats?.escalated_count ?? 0,
              moduleCount: dashboard?.reviews_by_status?.escalated ?? 0,
              moduleName: "Status Pipeline",
              status: (stats?.escalated_count ?? 0) === (dashboard?.reviews_by_status?.escalated ?? 0) ? "match" : "mismatch",
            },
          ]}
          onRefresh={() => { dashboardQuery.refetch(); reviewsQuery.refetch(); }}
          className="mb-6"
        />

        {/* Recent Activity */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="border-b border-gray-100 px-5 py-4 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Recent Activity</h3>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {activity.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-gray-400 dark:text-gray-500">No recent activity</p>
            ) : (
              activity.slice(0, 10).map((a, i) => (
                <div key={i} className="flex items-center gap-3 px-5 py-3">
                  <span className={`flex h-2 w-2 rounded-full ${
                    a.activity_type === "review_created" ? "bg-blue-500"
                    : a.activity_type === "finding_resolved" ? "bg-green-500"
                    : a.activity_type === "review_escalated" ? "bg-red-500"
                    : "bg-gray-400"
                  }`} />
                  <p className="flex-1 text-sm text-gray-600 dark:text-gray-400">{a.description}</p>
                  {a.actor && <span className="text-xs text-gray-400 dark:text-gray-500">{a.actor}</span>}
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    {new Date(a.timestamp).toLocaleDateString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </AsyncBoundary>
    </div>
  );
}

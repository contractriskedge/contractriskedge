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

import React from "react";
import {
  FileText, AlertTriangle, CheckCircle2, Clock, TrendingUp,
  Users, Activity, BarChart3, RefreshCw,
} from "lucide-react";
import { useReviewDashboard, useReviews } from "@/services/hooks";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";

// ── KPI Card ──

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  trend?: { value: number; positive: boolean };
}

function KpiCard({ title, value, subtitle, icon, color, trend }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
          {subtitle && (
            <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{subtitle}</p>
          )}
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}>
          {icon}
        </div>
      </div>
      {trend && (
        <div className="mt-3 flex items-center gap-1.5">
          <TrendingUp className={`h-3.5 w-3.5 ${trend.positive ? "text-green-500" : "text-red-500"}`} />
          <span className={`text-xs font-medium ${trend.positive ? "text-green-600" : "text-red-600"}`}>
            {trend.value}% {trend.positive ? "increase" : "decrease"}
          </span>
        </div>
      )}
    </div>
  );
}

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
  const dashboardQuery = useReviewDashboard();
  const reviewsQuery = useReviews({ page_size: 5 });

  const dashboard = dashboardQuery.data;
  const recentReviews = reviewsQuery.data?.data ?? [];

  const stats = dashboard?.stats;
  const severity = dashboard?.findings_by_severity ?? {};
  const statuses = dashboard?.reviews_by_status ?? {};
  const activity = dashboard?.recent_activity ?? [];
  const totalSeverity = Object.values(severity).reduce((a, b) => a + b, 0);

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
        loadingSkeleton={<CardSkeleton count={4} columns={4} />}
        onRetry={() => dashboardQuery.refetch()}
      >
        {/* KPI Row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            title="Total Reviews"
            value={stats?.total_reviews ?? 0}
            subtitle={`${stats?.completed_reviews ?? 0} completed`}
            icon={<FileText className="h-5 w-5 text-white" />}
            color="bg-blue-500"
          />
          <KpiCard
            title="Total Findings"
            value={stats?.total_findings ?? 0}
            subtitle={`${stats?.average_confidence ? `${Math.round(stats.average_confidence * 100)}% avg confidence` : ""}`}
            icon={<Activity className="h-5 w-5 text-white" />}
            color="bg-purple-500"
          />
          <KpiCard
            title="Pending Reviews"
            value={stats?.pending_reviews ?? 0}
            subtitle={`${stats?.sla_breach_count ?? 0} SLA breaches`}
            icon={<Clock className="h-5 w-5 text-white" />}
            color="bg-amber-500"
          />
          <KpiCard
            title="Escalated"
            value={stats?.escalated_count ?? 0}
            subtitle={`${dashboard?.sla_at_risk ?? 0} at risk`}
            icon={<AlertTriangle className="h-5 w-5 text-white" />}
            color="bg-red-500"
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

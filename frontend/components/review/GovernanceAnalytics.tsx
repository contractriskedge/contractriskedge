/**
 * GovernanceAnalytics — executive operational governance dashboard.
 *
 * Metrics:
 * - Avg review time
 * - Approval / rejection rates
 * - SLA breaches & overdue hours
 * - Reviewer workload (active vs completed)
 * - Escalation frequency
 * - Top failing clauses from rejected reviews
 */

"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import {
  Clock, ThumbsUp, ThumbsDown, AlertTriangle, User,
  ArrowUpRight, FileText, Loader2, TrendingUp, TrendingDown,
} from "lucide-react";

// ── Types ───────────────────────────────────────────────────────

interface GovernanceAnalyticsData {
  avg_review_time_hours: number;
  approval_rate: number;
  rejection_rate: number;
  total_approvals: number;
  total_rejections: number;
  sla_breach_count: number;
  avg_overdue_hours: number;
  escalation_frequency: number;
  reviewer_workload: Array<{
    reviewer: string;
    active_count: number;
    completed_count: number;
  }>;
  top_failing_clauses: Array<{
    clause_type: string;
    count: number;
  }>;
}

// ── Hook ────────────────────────────────────────────────────────

function useGovernanceAnalytics() {
  return useQuery<GovernanceAnalyticsData>({
    queryKey: ["reviews", "governance-analytics"],
    queryFn: () => api.get<GovernanceAnalyticsData>("/reviews/governance-analytics"),
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}

// ── Helpers ─────────────────────────────────────────────────────

function formatHours(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${Math.round(hours)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function formatClauseType(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Stat Card ───────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  subValue,
  trend,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  subValue?: string;
  trend?: "up" | "down";
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          {icon}
        </div>
        {trend && (
          <span className={`flex items-center gap-1 text-[10px] font-medium ${
            trend === "up" ? "text-red-500" : "text-green-500"
          }`}>
            {trend === "up" ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-navy-900">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
      {subValue && <p className="text-[10px] text-gray-400 mt-0.5">{subValue}</p>}
    </div>
  );
}

// ── Component ───────────────────────────────────────────────────

export function GovernanceAnalytics() {
  const { data, isLoading } = useGovernanceAnalytics();

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 flex justify-center">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* ── KPI Grid ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Clock className="w-5 h-5 text-blue-600" />}
          label="Avg Review Time"
          value={formatHours(data.avg_review_time_hours)}
          subValue={`${data.total_approvals + data.total_rejections} completed`}
          color="bg-blue-50"
        />
        <StatCard
          icon={<ThumbsUp className="w-5 h-5 text-green-600" />}
          label="Approval Rate"
          value={formatPercent(data.approval_rate)}
          subValue={`${data.total_approvals} approved`}
          trend="up"
          color="bg-green-50"
        />
        <StatCard
          icon={<ThumbsDown className="w-5 h-5 text-red-600" />}
          label="Rejection Rate"
          value={formatPercent(data.rejection_rate)}
          subValue={`${data.total_rejections} rejected`}
          trend={data.rejection_rate > 20 ? "up" : "down"}
          color="bg-red-50"
        />
        <StatCard
          icon={<AlertTriangle className="w-5 h-5 text-orange-600" />}
          label="SLA Breaches"
          value={String(data.sla_breach_count)}
          subValue={`Avg ${formatHours(data.avg_overdue_hours)} overdue`}
          trend={data.sla_breach_count > 0 ? "up" : "down"}
          color="bg-orange-50"
        />
      </div>

      {/* ── Secondary Metrics ── */}
      <div className="grid grid-cols-2 gap-4">
        {/* Reviewer Workload */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <User className="w-4 h-4 text-gray-500" />
            <h3 className="text-sm font-semibold text-navy-900">Reviewer Workload</h3>
          </div>
          {data.reviewer_workload.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-4">No reviewers with active reviews</p>
          ) : (
            <div className="space-y-2">
              {data.reviewer_workload.map((r) => (
                <div key={r.reviewer} className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                      <User className="w-3 h-3 text-gray-500" />
                    </div>
                    <span className="text-xs font-medium text-gray-700 truncate">{r.reviewer}</span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px]">
                    <span className="text-amber-600 font-medium">{r.active_count} active</span>
                    <span className="text-green-600 font-medium">{r.completed_count} done</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Failing Clauses */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-4 h-4 text-gray-500" />
            <h3 className="text-sm font-semibold text-navy-900">Top Failing Clauses</h3>
            <span className="text-[9px] text-gray-400">from rejected reviews</span>
          </div>
          {data.top_failing_clauses.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-4">No rejection data available</p>
          ) : (
            <div className="space-y-2">
              {data.top_failing_clauses.map((clause) => (
                <div key={clause.clause_type} className="flex items-center justify-between">
                  <span className="text-xs text-gray-700">{formatClauseType(clause.clause_type)}</span>
                  <span className="text-xs font-semibold text-red-600">{clause.count}x</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Escalation Frequency */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-2">
          <ArrowUpRight className="w-4 h-4 text-orange-500" />
          <h3 className="text-sm font-semibold text-navy-900">Escalation Frequency</h3>
          <span className="text-lg font-bold text-orange-600 ml-auto">{data.escalation_frequency}</span>
        </div>
        <p className="text-xs text-gray-500">
          Total escalations across all reviews. Each escalation represents a review that required hierarchical governance intervention.
        </p>
      </div>
    </div>
  );
}

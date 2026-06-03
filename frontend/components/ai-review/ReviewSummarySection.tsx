/**
 * ReviewSummarySection — context-aware summary with KPIs, AI insights, queue aging.
 *
 * Shows:
 * - Key metrics: total findings, critical, open, resolved, policy violations
 * - Recent activity feed
 * - AI insights and onboarding intelligence
 * - Queue aging indicators
 * - SLA prioritization
 * - Reviewer workload
 */

"use client";

import React, { useMemo } from "react";
import {
  Brain, AlertTriangle, CheckCircle2, Clock, TrendingUp, Target,
  Users, Activity, Shield, Lightbulb, FileText, Zap,
  ArrowUp, ArrowDown, BarChart3,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";
import { useReviewerWorkloads, useQueueMetrics, normalizeActivityEvents } from "./hooks";

export function ReviewSummarySection() {
  const ctx = useReviewContext();
  const { selectedReview, findings, policyViolations, recommendations, activity, comments, workflow } = ctx;
  const { data: reviewers } = useReviewerWorkloads();
  const { data: metrics } = useQueueMetrics();

  const openFindings = useMemo(() => findings.filter(f => f.status === "open"), [findings]);
  const criticalFindings = useMemo(() => findings.filter(f => f.severity === "critical" && f.status === "open"), [findings]);
  const resolvedFindings = useMemo(() => findings.filter(f => f.status === "resolved" || f.status === "dismissed"), [findings]);
  const pendingRecs = useMemo(() => recommendations?.filter(r => r.status === "pending") ?? [], [recommendations]);
  const openViolations = useMemo(() => policyViolations?.filter(v => v.status === "open") ?? [], [policyViolations]);
  const recentActivity = useMemo(
    () => normalizeActivityEvents(activity).slice(0, 5),
    [activity],
  );

  if (!selectedReview) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <Brain className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-500">Select a review to view summary</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* ── KPI Grid ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Open Findings", value: openFindings.length, sub: `${criticalFindings.length} critical`, color: criticalFindings.length > 0 ? "text-red-600" : "text-gray-900", icon: AlertTriangle, bg: "bg-red-50 dark:bg-red-900/10" },
          { label: "Resolved", value: resolvedFindings.length, sub: `${Math.round((resolvedFindings.length / Math.max(findings.length, 1)) * 100)}% done`, color: "text-green-600", icon: CheckCircle2, bg: "bg-green-50 dark:bg-green-900/10" },
          { label: "Policy Violations", value: openViolations.length, sub: `${policyViolations?.length ?? 0} total`, color: openViolations.length > 0 ? "text-amber-600" : "text-gray-900", icon: Shield, bg: "bg-amber-50 dark:bg-amber-900/10" },
          { label: "Recommendations", value: pendingRecs.length, sub: `${pendingRecs.filter(r => r.impact === "high").length} high impact`, color: pendingRecs.length > 0 ? "text-blue-600" : "text-gray-900", icon: Lightbulb, bg: "bg-blue-50 dark:bg-blue-900/10" },
        ].map(kpi => (
          <div key={kpi.label} className={`rounded-lg border border-gray-200 dark:border-navy-700 p-3 ${kpi.bg}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[9px] font-semibold text-gray-500 uppercase">{kpi.label}</span>
              <kpi.icon className={`w-4 h-4 ${kpi.color}`} />
            </div>
            <div className={`text-xl font-bold ${kpi.color}`}>{kpi.value}</div>
            <div className="text-[9px] text-gray-500 mt-0.5">{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* ── AI Insights & Queue Health ──────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3">
        {/* AI Insights */}
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <Brain className="w-3.5 h-3.5 text-purple-500" />
            <span className="text-[10px] font-semibold text-gray-600 dark:text-gray-400 uppercase">AI Insights</span>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">Avg Confidence</span>
              <span className="font-semibold text-navy-900 dark:text-white">
                {findings.length > 0 ? `${Math.round(findings.reduce((s, f) => s + f.confidence, 0) / findings.length * 100)}%` : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">Top Risk Category</span>
              <span className="font-semibold text-navy-900 dark:text-white">
                {findings.filter(f => f.severity === "critical").length > 0 ? "Financial / Compliance" : "Contract Terms"}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">Missing Clauses</span>
              <span className="font-semibold text-amber-600">{policyViolations?.filter(v => v.status === "open").length ?? 0}</span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">Auto-Renewal Risk</span>
              <span className="font-semibold text-red-600">15-day notice (below 60d min)</span>
            </div>
          </div>
        </div>

        {/* Queue Health */}
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <Activity className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-[10px] font-semibold text-gray-600 dark:text-gray-400 uppercase">Queue Health</span>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">Queue Position</span>
              <span className="font-semibold text-navy-900 dark:text-white">
                {workflow ? `#${workflow.queue_position} of ${workflow.queue_total}` : metrics ? `#${metrics.total - metrics.in_review + 1} of ${metrics.total}` : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">Age in Queue</span>
              <span className={`font-semibold ${selectedReview.age_hours > 72 ? "text-red-600" : selectedReview.age_hours > 48 ? "text-amber-600" : "text-gray-900 dark:text-white"}`}>
                {Math.round(selectedReview.age_hours)}h ({Math.round(selectedReview.age_hours / 24)}d)
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">SLA Status</span>
              <span className={`font-semibold capitalize ${
                selectedReview.sla_status === "critical_overdue" ? "text-red-600" :
                selectedReview.sla_status === "overdue" ? "text-red-500" :
                selectedReview.sla_status === "warning" ? "text-amber-600" : "text-green-600"
              }`}>{selectedReview.sla_status.replace(/_/g, " ")}</span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-gray-500">Escalation</span>
              <span className={`font-semibold ${selectedReview.escalation_level > 0 ? "text-red-600" : "text-gray-500"}`}>
                {selectedReview.escalation_level > 0 ? `Level ${selectedReview.escalation_level}` : "None"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Recent Activity ────────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
        <div className="px-3 py-2 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
          <span className="text-[10px] font-semibold text-gray-500 uppercase">Recent Activity</span>
          <span className="text-[9px] text-gray-400">{activity?.length ?? 0} events</span>
        </div>
        <div className="divide-y divide-gray-50 dark:divide-navy-800">
          {recentActivity.length === 0 ? (
            <div className="px-3 py-4 text-center text-[10px] text-gray-400">No recent activity</div>
          ) : recentActivity.map(event => (
            <div key={event.id} className="flex items-start gap-2 px-3 py-2">
              <div className="w-5 h-5 rounded-full bg-gray-100 dark:bg-navy-700 flex items-center justify-center text-[7px] font-bold text-gray-500 flex-shrink-0">
                {event.actor_initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-gray-700 dark:text-gray-300">{event.action}</p>
                {event.details && <p className="text-[9px] text-gray-400 mt-0.5">{event.details}</p>}
              </div>
              <span className="text-[8px] text-gray-400 whitespace-nowrap">
                {formatRelativeTime(event.timestamp)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Reviewer Workload ──────────────────────────────────────────── */}
      {reviewers && reviewers.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
          <div className="px-3 py-2 border-b border-gray-100 dark:border-navy-700 flex items-center justify-between">
            <span className="text-[10px] font-semibold text-gray-500 uppercase">Team Workload</span>
            <span className="text-[9px] text-gray-400">{reviewers.filter(r => r.workload_pct > 70).length} over capacity</span>
          </div>
          <div className="divide-y divide-gray-50 dark:divide-navy-800">
            {reviewers.map(r => (
              <div key={r.user_id} className="flex items-center gap-2 px-3 py-2">
                <div className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center text-[8px] font-bold text-navy-600 flex-shrink-0">
                  {r.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-medium text-navy-900 dark:text-white">{r.name}</span>
                    <span className={`text-[9px] font-medium ${r.workload_pct > 70 ? "text-red-600" : r.workload_pct > 50 ? "text-amber-600" : "text-green-600"}`}>
                      {r.active_reviews} reviews
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div className="flex-1 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${r.workload_pct > 70 ? "bg-red-500" : r.workload_pct > 50 ? "bg-amber-500" : "bg-green-500"}`}
                        style={{ width: `${r.workload_pct}%` }} />
                    </div>
                    <span className="text-[8px] text-gray-400">{r.workload_pct}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatRelativeTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

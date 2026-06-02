/**
 * ReviewerLoadWidget — Workload distribution, pending approvals, escalation hotspots.
 *
 * Shows:
 * - Workload heatmap (reviewer x status)
 * - Pending approval badges
 * - Escalation trend line
 * - Bottleneck callout cards
 * - Capacity alert when any reviewer exceeds 80% utilization
 */

"use client";

import React from "react";

interface ReviewerLoadData {
  reviewers: {
    name: string;
    assigned: number;
    inReview: number;
    pendingApproval: number;
    completed: number;
    utilization: number; // 0-1
  }[];
  pendingApprovalsTotal: number;
  escalationRate: number; // 0-1
  escalationTrend: number[]; // 7 days
  bottlenecks: { stage: string; severity: "high" | "medium" | "low"; description: string }[];
}

interface ReviewerLoadWidgetProps {
  reviewerData?: import("@/src/lib/executive/executiveTypes").ReviewerEfficiency | null;
}

export function ReviewerLoadWidget({ reviewerData }: ReviewerLoadWidgetProps) {
  if (!reviewerData) {
    return (
      <div className="flex items-center justify-center h-32 text-xs text-gray-400">
        No reviewer data available
      </div>
    );
  }

  const overloadedReviewers = reviewerData.reviewer_details.filter((r) => r.is_overloaded);

  return (
    <div className="space-y-3">
      {/* ── Capacity Alert ────────────────────────────────────── */}
      {overloadedReviewers.length > 0 && (
        <div className="px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-xs font-medium text-red-700 dark:text-red-300">
            ⚠ {overloadedReviewers.length} reviewer{overloadedReviewers.length > 1 ? "s" : ""} at capacity
            ({overloadedReviewers.map((r) => r.name).join(", ")})
          </p>
        </div>
      )}

      {/* ── Summary KPIs ── */}
      <div className="grid grid-cols-3 gap-2">
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-navy-700 text-center">
          <span className="text-lg font-bold text-navy-900 dark:text-white">{reviewerData.reviewer_details.length}</span>
          <p className="text-[10px] text-gray-500">Active Reviewers</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-navy-700 text-center">
          <span className="text-lg font-bold text-amber-600 dark:text-amber-400">{reviewerData.reviewer_backlog}</span>
          <p className="text-[10px] text-gray-500">Backlog</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-navy-700 text-center">
          <span className="text-lg font-bold text-navy-900 dark:text-white">
            {reviewerData.avg_review_completion_hours.toFixed(1)}h
          </span>
          <p className="text-[10px] text-gray-500">Avg Completion</p>
        </div>
      </div>

      {/* ── Reviewer Workload Table ── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Reviewer Workload
        </span>
        <div className="space-y-1">
          {reviewerData.reviewer_details.map((reviewer) => {
            const active = reviewer.active_reviews + reviewer.completed_reviews;
            const capacity = 20;
            const utilization = Math.min(active / capacity, 1);
            return (
              <div key={reviewer.reviewer_id} className="flex items-center gap-2">
                <span className="text-xs text-gray-600 dark:text-gray-400 w-24 truncate" title={reviewer.reviewer_name}>
                  {reviewer.reviewer_name}
                </span>
                <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${utilization * 100}%`,
                      backgroundColor: utilization >= 0.8 ? "#EF4444" : utilization >= 0.6 ? "#F59E0B" : "#10B981",
                    }}
                  />
                </div>
                <span className={`text-xs font-medium w-8 text-right ${
                  utilization >= 0.8 ? "text-red-600" : "text-navy-900 dark:text-white"
                }`}>
                  {Math.round(utilization * 100)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Bottlenecks ── */}
      {reviewerData.reviewer_details.filter((r) => r.is_overloaded).length > 0 && (
        <div>
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
            Overloaded Reviewers
          </span>
          <div className="space-y-1">
            {reviewerData.reviewer_details.filter((r) => r.is_overloaded).map((r) => (
              <div key={r.reviewer_id} className="px-2 py-1.5 rounded-lg text-xs bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300">
                <span className="font-medium">{r.reviewer_name}:</span> {r.active_reviews} active, {r.backlog_hours.toFixed(0)}h backlog
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

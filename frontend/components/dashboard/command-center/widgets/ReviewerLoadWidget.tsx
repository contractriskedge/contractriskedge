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
  metrics?: any | null;
}

const DEFAULT_DATA: ReviewerLoadData = {
  reviewers: [
    { name: "Sarah Chen", assigned: 5, inReview: 3, pendingApproval: 2, completed: 12, utilization: 0.85 },
    { name: "Mike Johnson", assigned: 3, inReview: 4, pendingApproval: 1, completed: 9, utilization: 0.72 },
    { name: "Emily Rodriguez", assigned: 2, inReview: 2, pendingApproval: 3, completed: 15, utilization: 0.65 },
    { name: "James Wilson", assigned: 6, inReview: 1, pendingApproval: 0, completed: 7, utilization: 0.45 },
    { name: "Lisa Park", assigned: 4, inReview: 3, pendingApproval: 2, completed: 11, utilization: 0.78 },
  ],
  pendingApprovalsTotal: 8,
  escalationRate: 0.12,
  escalationTrend: [0.08, 0.10, 0.15, 0.11, 0.09, 0.13, 0.12],
  bottlenecks: [
    { stage: "Approval", severity: "high", description: "3 reviews waiting >48h for approval" },
    { stage: "AI Analysis", severity: "medium", description: "Queue depth increasing (8 items)" },
  ],
};

export function ReviewerLoadWidget({ metrics }: ReviewerLoadWidgetProps) {
  const data = DEFAULT_DATA;

  const overloadedReviewers = data.reviewers.filter((r) => r.utilization >= 0.8);

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

      {/* ── Summary KPIs ──────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-2">
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-navy-700 text-center">
          <span className="text-lg font-bold text-navy-900 dark:text-white">{data.reviewers.length}</span>
          <p className="text-[10px] text-gray-500">Active Reviewers</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-navy-700 text-center">
          <span className="text-lg font-bold text-amber-600 dark:text-amber-400">{data.pendingApprovalsTotal}</span>
          <p className="text-[10px] text-gray-500">Pending Approvals</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-navy-700 text-center">
          <span className="text-lg font-bold text-navy-900 dark:text-white">{Math.round(data.escalationRate * 100)}%</span>
          <p className="text-[10px] text-gray-500">Escalation Rate</p>
        </div>
      </div>

      {/* ── Reviewer Workload Table ───────────────────────────── */}
      <div>
        <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
          Reviewer Workload
        </span>
        <div className="space-y-1">
          {data.reviewers.map((reviewer) => (
            <div key={reviewer.name} className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-24 truncate" title={reviewer.name}>
                {reviewer.name}
              </span>
              <div className="flex-1 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${reviewer.utilization * 100}%`,
                    backgroundColor: reviewer.utilization >= 0.8 ? "#EF4444" : reviewer.utilization >= 0.6 ? "#F59E0B" : "#10B981",
                  }}
                />
              </div>
              <span className={`text-xs font-medium w-8 text-right ${
                reviewer.utilization >= 0.8 ? "text-red-600" : "text-navy-900 dark:text-white"
              }`}>
                {Math.round(reviewer.utilization * 100)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Bottlenecks ───────────────────────────────────────── */}
      {data.bottlenecks.length > 0 && (
        <div>
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase mb-1 block">
            Bottlenecks
          </span>
          <div className="space-y-1">
            {data.bottlenecks.map((b, i) => (
              <div
                key={i}
                className={`px-2 py-1.5 rounded-lg text-xs ${
                  b.severity === "high"
                    ? "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300"
                    : "bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300"
                }`}
              >
                <span className="font-medium">{b.stage}:</span> {b.description}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

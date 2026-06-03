/**
 * Helpers for review approve/reject UI — hide actions when workflow is terminal.
 */

import type { ReviewSummary, WorkflowState } from "./types";

const TERMINAL_REVIEW_STATUSES = new Set<ReviewSummary["status"]>([
  "approved",
  "rejected",
  "archived",
]);

const TERMINAL_WORKFLOW_STAGES = new Set([
  "completed",
  "archived",
  "executed",
  "finalized",
  "closed",
  "approved",
  "rejected",
]);

/** True when approve/reject actions must not be shown (read-only / completed). */
export function isReviewDecisionLocked(
  review: ReviewSummary,
  workflow?: WorkflowState | null,
): boolean {
  if (TERMINAL_REVIEW_STATUSES.has(review.status)) return true;
  if (TERMINAL_WORKFLOW_STAGES.has(review.workflow_stage)) return true;
  if (review.completed_at) return true;
  if (workflow && TERMINAL_WORKFLOW_STAGES.has(workflow.current_stage)) return true;

  if (workflow?.stages.length) {
    const finalStage = workflow.stages[workflow.stages.length - 1]!;
    const isCompletedFinal =
      (finalStage.id === "completed" ||
        finalStage.label.toLowerCase() === "completed") &&
      (finalStage.status === "completed" || finalStage.status === "current");
    const otherCurrent = workflow.stages.some(
      (s) => s.status === "current" && s.id !== finalStage.id,
    );
    if (isCompletedFinal && !otherCurrent) return true;
  }

  return false;
}

export function formatReviewStatusLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function reviewStatusBadgeClass(status: string): string {
  switch (status) {
    case "approved":
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300";
    case "rejected":
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
    case "archived":
      return "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
    case "escalated":
      return "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300";
    case "completed":
      return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
    default:
      return "bg-navy-100 text-navy-700 dark:bg-navy-700 dark:text-navy-200";
  }
}

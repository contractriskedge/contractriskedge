/**
 * Workflow status helpers — shared utilities for frontend workflow state awareness.
 *
 * Provides:
 * - Immutable state detection (read-only)
 * - Mutable state detection (editable)
 * - Allowed action checks per status
 * - Human-readable status labels
 * - Status color mapping
 */

// ── Workflow States — Enterprise Lifecycle ────────────────────────
// Complete contract review lifecycle:
//   Upload → AI Analysis → Under Review → Legal/Procurement/Security Review
//   → Approved → Negotiation Sent → Executed → Archived

export const WORKFLOW_STATES = {
  UPLOADED: "uploaded",
  AI_ANALYZED: "ai_analyzed",
  REVIEW_READY: "review_ready",
  IN_REVIEW: "in_review",
  LEGAL_REVIEW: "legal_review",
  LEGAL_APPROVAL: "legal_approval",
  EXEC_APPROVAL: "exec_approval",
  PROCUREMENT_REVIEW: "procurement_review",
  SECURITY_REVIEW: "security_review",
  ESCALATED: "escalated",
  APPROVED: "approved",
  REJECTED: "rejected",
  CLOSED: "closed",
  FINALIZED: "finalized",
  EXECUTED: "executed",
  ARCHIVED: "archived",
} as const;

export type WorkflowState = (typeof WORKFLOW_STATES)[keyof typeof WORKFLOW_STATES];

// ── Immutable States (read-only) ─────────────────────────────────

const IMMUTABLE_STATES: Set<string> = new Set([
  WORKFLOW_STATES.EXECUTED,
  WORKFLOW_STATES.ARCHIVED,
]);

export function isImmutable(status: string): boolean {
  return IMMUTABLE_STATES.has(status);
}

export function isMutable(status: string): boolean {
  return !IMMUTABLE_STATES.has(status);
}

// ── Allowed Actions Per Status ───────────────────────────────────

interface AllowedActions {
  canEditRedlines: boolean;
  canResolveFindings: boolean;
  canApprove: boolean;
  canReject: boolean;
  canEscalate: boolean;
  canAssign: boolean;
  canReAnalyze: boolean;
  canFinalize: boolean;
  canArchive: boolean;
  canDelete: boolean;
  canComment: boolean;
  canBulkAction: boolean;
}

export function getAllowedActions(status: string): AllowedActions {
  const immutable = isImmutable(status);
  const s = status;

  return {
    canEditRedlines: !immutable,
    canResolveFindings: !immutable,
    canApprove: s === WORKFLOW_STATES.LEGAL_APPROVAL || s === WORKFLOW_STATES.EXEC_APPROVAL || s === WORKFLOW_STATES.LEGAL_REVIEW || s === WORKFLOW_STATES.ESCALATED || s === WORKFLOW_STATES.SECURITY_REVIEW,
    canReject: s === WORKFLOW_STATES.LEGAL_APPROVAL || s === WORKFLOW_STATES.EXEC_APPROVAL || s === WORKFLOW_STATES.LEGAL_REVIEW || s === WORKFLOW_STATES.ESCALATED || s === WORKFLOW_STATES.SECURITY_REVIEW,
    canEscalate: !immutable && s !== WORKFLOW_STATES.ARCHIVED,
    canAssign: !immutable,
    canReAnalyze: !immutable,
    canFinalize: s === WORKFLOW_STATES.APPROVED,
    canArchive: !immutable && s !== WORKFLOW_STATES.ARCHIVED,
    canDelete: !immutable,
    canComment: true,
    canBulkAction: !immutable,
  };
}

// ── Status Display ───────────────────────────────────────────────

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    uploaded: "Uploaded",
    ai_analyzed: "AI Analyzed",
    review_ready: "Review Ready",
    in_review: "In Review",
    legal_review: "Legal Review",
    legal_approval: "Legal Approval",
    exec_approval: "Executive Approval",
    procurement_review: "Procurement Review",
    security_review: "Security Review",
    escalated: "Escalated",
    approved: "Approved",
    rejected: "Rejected",
    closed: "Closed",
    finalized: "Finalized",
    executed: "Executed",
    archived: "Archived",
  };
  return labels[status] || status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    uploaded: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    ai_analyzed: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
    review_ready: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
    in_review: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
    legal_review: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
    legal_approval: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
    exec_approval: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    procurement_review: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
    security_review: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
    escalated: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    approved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    rejected: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    closed: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
    finalized: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    executed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    archived: "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400",
  };
  return colors[status] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
}

// ── Immutable Banner ─────────────────────────────────────────────

export function getImmutableBannerInfo(status: string): { title: string; description: string; color: string } | null {
  if (!isImmutable(status)) return null;

  const banners: Record<string, { title: string; description: string; color: string }> = {
    executed: {
      title: "Contract Executed — Immutable",
      description: "This contract has been executed. All content is locked permanently for audit purposes.",
      color: "border-emerald-400 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-700",
    },
    archived: {
      title: "Review Archived — Read Only",
      description: "This review has been archived. Content is locked and preserved for audit purposes.",
      color: "border-gray-400 bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600",
    },
    approved: {
      title: "Review Approved — Read Only",
      description: "This review has been approved. Content is locked for audit purposes.",
      color: "border-green-400 bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
    },
    rejected: {
      title: "Review Rejected — Read Only",
      description: "This review has been rejected. Content is locked for audit purposes.",
      color: "border-red-400 bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
    },
    closed: {
      title: "Review Closed — Read Only",
      description: "This review has been closed. Content is locked for audit purposes.",
      color: "border-gray-400 bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600",
    },
    finalized: {
      title: "Review Finalized — Immutable",
      description: "This review has been finalized. All content is locked permanently.",
      color: "border-emerald-400 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-700",
    },
  };

  return banners[status] || null;
}

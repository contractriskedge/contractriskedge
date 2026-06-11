/**
 * Contract Repository lifecycle stages.
 *
 * Flow: Draft → Review → Approved → Active → Expiring → Closed
 *
 * Maps review/contract status + SLA + expiry into a single badge for the table.
 * Aligns with Review Queue lifecycle badges (executed+SLA, approved, archived, etc.).
 */

import type { ContractRecord } from "./types";

export type ContractLifecycleStage =
  | "draft"
  | "review"
  | "approved"
  | "active"
  | "expiring"
  | "closed";

export const CONTRACT_LIFECYCLE_ORDER: ContractLifecycleStage[] = [
  "draft",
  "review",
  "approved",
  "active",
  "expiring",
  "closed",
];

export const CONTRACT_LIFECYCLE_CONFIG: Record<
  ContractLifecycleStage,
  { label: string; color: string; bg: string; darkColor: string; darkBg: string }
> = {
  draft: {
    label: "Draft",
    color: "text-slate-700",
    bg: "bg-slate-100",
    darkColor: "dark:text-slate-300",
    darkBg: "dark:bg-slate-800",
  },
  review: {
    label: "Review",
    color: "text-amber-700",
    bg: "bg-amber-100",
    darkColor: "dark:text-amber-300",
    darkBg: "dark:bg-amber-900/20",
  },
  approved: {
    label: "Approved",
    color: "text-blue-700",
    bg: "bg-blue-100",
    darkColor: "dark:text-blue-300",
    darkBg: "dark:bg-blue-900/20",
  },
  active: {
    label: "Active",
    color: "text-green-700",
    bg: "bg-green-100",
    darkColor: "dark:text-green-300",
    darkBg: "dark:bg-green-900/20",
  },
  expiring: {
    label: "Expiring",
    color: "text-orange-700",
    bg: "bg-orange-100",
    darkColor: "dark:text-orange-300",
    darkBg: "dark:bg-orange-900/20",
  },
  closed: {
    label: "Closed",
    color: "text-gray-600",
    bg: "bg-gray-100",
    darkColor: "dark:text-gray-400",
    darkBg: "dark:bg-navy-700",
  },
};

const REVIEW_STAGE_STATUSES = new Set([
  "uploaded",
  "analyzing",
  "ai_analyzed",
  "ai_reviewed",
  "review_ready",
  "in_review",
  "under_review",
  "procurement_review",
  "legal_review",
  "security_review",
  "negotiation",
  "changes_requested",
  "pending_approval",
  "escalated",
  "legal_approval",
  "exec_approval",
]);

/** Resolve raw review status when API omits reviewStatus (legacy rows). */
export function resolveReviewStatus(c: ContractRecord): string {
  if (c.reviewStatus) return c.reviewStatus.toLowerCase();
  const st = (c.status || "").toLowerCase();
  const wf = (c.workflowStage || "").toLowerCase();
  if (wf === "archived" || st === "expired") return "archived";
  if (wf === "executed" || st === "active") return "executed";
  if (st === "under_review" || wf === "review" || wf === "negotiation") return "in_review";
  if (st === "pending_review" || wf === "approval") return "pending_approval";
  if (st === "expiring_soon") return "executed";
  return st || "draft";
}

/** Derive lifecycle stage badge for a contract row. */
export function contractLifecycleFor(c: ContractRecord): ContractLifecycleStage {
  const rs = resolveReviewStatus(c);
  const sla = (c.slaStatus || "").toLowerCase();
  const health = c.health || "";
  const st = (c.status || "").toLowerCase();

  // Closed — archived / closed reviews
  if (rs === "archived" || rs === "closed") return "closed";

  // Expiring — renewal window, past expiry, or executed with overdue SLA
  if (
    health === "expiring_soon" ||
    health === "expired" ||
    st === "expiring_soon" ||
    st === "expired" ||
    st === "renewal_at_risk" ||
    (rs === "executed" && (sla === "overdue" || sla === "critical_overdue"))
  ) {
    return "expiring";
  }

  // Active — executed / finalized with healthy SLA
  if (rs === "executed" || rs === "finalized") return "active";

  // Approved — signed off, not yet executed
  if (rs === "approved" || rs === "conditionally_approved") return "approved";

  // Review — any in-flight review or approval workflow
  if (
    REVIEW_STAGE_STATUSES.has(rs) ||
    st === "under_review" ||
    st === "pending_review" ||
    st === "awaiting_legal" ||
    st === "compliance_needed"
  ) {
    return "review";
  }

  return "draft";
}

/** Human-readable review status for the Status column. */
export function formatReviewStatusLabel(c: ContractRecord): string {
  const rs = resolveReviewStatus(c);
  const labels: Record<string, string> = {
    draft: "Draft",
    uploaded: "Uploaded",
    analyzing: "Analyzing",
    ai_analyzed: "AI Analyzed",
    in_review: "In Review",
    under_review: "Under Review",
    pending_approval: "Pending Approval",
    approved: "Approved",
    conditionally_approved: "Cond. Approved",
    rejected: "Rejected",
    finalized: "Finalized",
    executed: "Executed",
    archived: "Archived",
    closed: "Closed",
    escalated: "Escalated",
    negotiation: "Negotiation",
  };
  return labels[rs] || rs.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
}

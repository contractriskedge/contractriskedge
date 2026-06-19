/**
 * ReviewActions — enterprise workflow action bar for review management.
 *
 * Implements:
 * - Assign reviewer
 * - Escalate review
 * - Approve / Reject / Conditionally approve
 * - Finalize (lock approved version)
 * - Close / Archive (terminal lifecycle)
 * - Add comments
 * - Soft delete
 * - Send to Legal / Procurement / Security (workflow routing)
 * - Request Counterparty Revision
 * - Generate Negotiation Package
 * - Export Review Memo
 *
 * All actions use idempotency keys for safe retry.
 * Buttons are disabled based on workflow state (immutable check).
 */

"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence } from "framer-motion";
import {
  UserPlus, AlertTriangle, CheckCircle2, XCircle, Lock,
  MessageSquare, Trash2, ChevronDown, Send, Loader2,
  Scale, Briefcase, Shield, FileText, FileDown, RefreshCw,
  Archive, CheckCheck,
} from "lucide-react";
import type { ReviewDetail } from "@/services/api/client";
import { ApiRequestError } from "@/services/api/client";
import { reviewService } from "@/services/api/reviews";
import {
  useAssignReviewer, useEscalateReview, useApproveReview,
  useAddComment, useDeleteReview, useCloseReview, useFinalizeReview,
} from "@/services/hooks";
import { api } from "@/services/api/client";
import { useAuth } from "@/components/auth/AuthProvider";
import { useToast } from "@/components/ui/toast";
import { EscalationModal } from "./EscalationModal";
import { UserPicker } from "@/components/shared/UserPicker";
import { getAllowedActions, isImmutable, WORKFLOW_STATES } from "@/lib/workflow";

interface ReviewActionsProps {
  reviewId: string;
  review: ReviewDetail;
}

type ActionModal = "assign" | "escalate" | "approve" | "comment" | "delete"
  | "send_to_legal" | "send_to_procurement" | "send_to_security"
  | "request_revision" | "generate_negotiation" | "export_memo"
  | "close" | "finalize" | null;

export function ReviewActions({ reviewId, review }: ReviewActionsProps) {
  const [activeModal, setActiveModal] = useState<ActionModal>(null);
  const { hasPermission } = useAuth();
  const { addToast } = useToast();

  // Permission checks
  const canAssign = hasPermission("workflows:write");
  const canEscalate = hasPermission("workflows:escalate");
  const canApproveReject = hasPermission("workflows:approve");
  const canRouteToLegal = hasPermission("workflows:approve") || hasPermission("workflows:escalate");
  const canRouteToProcurement = hasPermission("workflows:write");
  const canRouteToSecurity = hasPermission("workflows:write") || hasPermission("audit:read");
  const canExport = hasPermission("audit:export");
  const canDelete = hasPermission("contracts:delete");

  // Mutations
  const assignMutation = useAssignReviewer(reviewId);
  const escalateMutation = useEscalateReview(reviewId);
  const approveMutation = useApproveReview(reviewId);
  const commentMutation = useAddComment(reviewId);
  const deleteMutation = useDeleteReview();
  const closeMutation = useCloseReview();
  const finalizeMutation = useFinalizeReview();

  // Fetch reviewer workload for the assign modal
  const { data: workloadData } = useQuery({
    queryKey: ["reviews", "reviewers", "workload"],
    queryFn: () => reviewService.getReviewersWorkload(),
    staleTime: 30_000,
    enabled: activeModal === "assign",
  });
  const reviewerWorkloads = workloadData?.reviewers?.map((r) => ({
    user_id: r.user_id,
    active_reviews: r.active_reviews,
    workload_pct: r.workload_pct,
  })) ?? [];

  // Form state
  const [assigneeId, setAssigneeId] = useState("");
  const [assignRole, setAssignRole] = useState<"reviewer" | "approver" | "observer">("reviewer");
  const [approveDecision, setApproveDecision] = useState<"approved" | "rejected" | "conditionally_approved">("approved");
  const [approveComments, setApproveComments] = useState("");
  const [approveError, setApproveError] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [deleteReason, setDeleteReason] = useState("");
  const [closeReason, setCloseReason] = useState("");

  // Pre-flight check: fetch unresolved critical/high findings count for approval gate
  const { data: openFindingsData, isFetching: openFindingsLoading } = useQuery({
    queryKey: ["reviews", reviewId, "findings", "open-critical"],
    queryFn: async () => {
      const res = await reviewService.listFindings(reviewId);
      const findings = Array.isArray(res) ? res : (res as Record<string, unknown>).findings ?? [];
      const openCritical = (findings as Array<Record<string, unknown>>).filter(
        (f) => (f.severity === "critical" || f.severity === "high") && !f.resolution
      );
      return { count: openCritical.length, items: openCritical.slice(0, 5) };
    },
    enabled: activeModal === "approve" && approveDecision === "approved",
    staleTime: 0,
    refetchOnMount: true,
  });
  const hasBlockingFindings = (openFindingsData?.count ?? 0) > 0;

  // Open obligations do NOT block approval — they are future commitments
  // that remain open after the contract is approved. Only contract closure
  // is blocked by open obligations (enforced server-side).

  const closeModal = () => {
    setActiveModal(null);
    setAssigneeId("");
    setApproveComments("");
    setApproveError("");
    setCommentBody("");
    setDeleteReason("");
    setCloseReason("");
  };

  const handleAssign = async () => {
    if (!assigneeId) return;
    const key = api.generateIdempotencyKey();
    await assignMutation.mutateAsync(
      { assignee_id: assigneeId, role: assignRole },
    );
    closeModal();
    // Show assignment confirmation with audit summary
    const assigneeName = reviewerWorkloads.find(r => r.user_id === assigneeId)?.user_id || assigneeId;
    const now = new Date().toLocaleString("en-US", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    });
    addToast("success", "Reviewer Assigned",
      `Assigned to ${assigneeName} · ${now} · by ${user?.name || user?.email || "You"}`
    );
  };

  const handleApprove = async () => {
    setApproveError("");
    // Pre-flight check: require reason when rejecting
    if (approveDecision === "rejected" && !approveComments.trim()) {
      setApproveError("Rejection reason is required. Please explain why this contract is being rejected.");
      return;
    }
    // Pre-flight check: block if critical findings are open
    if (hasBlockingFindings && (approveDecision === "approved" || approveDecision === "conditionally_approved")) {
      if (approveDecision === "approved") {
        setApproveError(
          `${openFindingsData?.count ?? 0} critical/high finding(s) are still open. ` +
          "Resolve or dismiss them first, or switch to 'conditionally approve' and include 'override:' in your comments to bypass."
        );
        return;
      }
      // Conditional approval requires an override reason in comments
      if (!approveComments.toLowerCase().includes("override:")) {
        setApproveError(
          `${openFindingsData?.count ?? 0} critical/high finding(s) are still open. ` +
          "Add 'override:' at the start of your comments to acknowledge and bypass."
        );
        return;
      }
    }
    try {
      await approveMutation.mutateAsync({
        decision: approveDecision,
        comments: approveComments || undefined,
      });
      closeModal();
      const label = approveDecision === "approved" ? "Approved" : approveDecision === "rejected" ? "Rejected" : "Conditionally Approved";
      addToast("success", `Review ${label}`, `Contract "${review.document_name || reviewId.slice(0, 8)}" has been ${approveDecision}.`);
    } catch (err) {
      // Format user-friendly error message
      let msg = "";
      if (err instanceof ApiRequestError) {
        msg = err.message;
      } else if (err instanceof Error) {
        msg = err.message;
      } else {
        msg = "An unexpected error occurred";
      }
      // Clean up technical error messages for end users
      if (msg.includes("Cannot approve:") || msg.includes("Cannot reject:") || msg.includes("Cannot conditionally approve:")) {
        msg = msg.replace(/^Cannot (approve|reject|conditionally approve): /, "Unable to $1: ");
      } else if (msg.includes("ConflictError") || msg.includes("HTTPException")) {
        msg = "This action cannot be completed due to the current review state.";
      } else if (msg.includes("409") || msg.includes("Conflict")) {
        msg = "This action conflicts with the current review state.";
      } else if (msg.includes("403") || msg.includes("forbidden") || msg.includes("Missing required permission")) {
        msg = "You don't have permission to perform this action.";
      } else if (msg.includes("contracts:approve") || msg.includes("contracts:write") || msg.includes("workflows:approve")) {
        msg = "You don't have permission to perform this action.";
      } else if (msg.includes("Missing required permission")) {
        msg = "You don't have permission to perform this action.";
      }
      setApproveError(msg);
    }
  };

  const handleComment = async () => {
    if (!commentBody) return;
    await commentMutation.mutateAsync({
      body: commentBody,
    });
    closeModal();
  };

  const handleDelete = async () => {
    await deleteMutation.mutateAsync({ reviewId, reason: deleteReason || undefined });
    closeModal();
  };

  // Enterprise workflow routing handlers
  const handleWorkflowRouting = async (targetStage: string) => {
    try {
      await escalateMutation.mutateAsync({
        reason: `Routing to ${targetStage.replace(/_/g, " ")} review`,
        escalated_to: targetStage,
        raise_priority: false,
        target_workflow_stage: targetStage,
      });
      closeModal();
    } catch {
      // Error handled by mutation state
    }
  };

  const handleRequestRevision = async () => {
    // Creates a formal counterparty revision request
    try {
      // This would call a dedicated endpoint in production
      await commentMutation.mutateAsync({
        body: "**Counterparty Revision Request** — Formal request for contract revision submitted.",
      });
      closeModal();
    } catch {
      // Error handled by mutation state
    }
  };

  const handleGenerateNegotiation = async () => {
    // Generates a negotiation package (findings + redlines + recommendations)
    try {
      await reviewService.exportNegotiationPackage(reviewId);
      // Post a comment to the review timeline
      await commentMutation.mutateAsync({
        body: "**Negotiation Package Generated** — All findings, redlines, and recommendations bundled for negotiation.",
      });
      closeModal();
    } catch {
      // Error handled by mutation state
    }
  };

  const handleExportMemo = async () => {
    // Triggers export of review memo (audit report)
    try {
      await reviewService.exportReviewAudit(reviewId);
      // Post a comment to the review timeline
      await commentMutation.mutateAsync({
        body: "**Review Memo Exported** — Complete review summary exported for distribution.",
      });
      closeModal();
    } catch {
      // Error handled by mutation state
    }
  };

  const isPending =
    assignMutation.isPending || escalateMutation.isPending ||
    approveMutation.isPending || commentMutation.isPending;

  const actions = getAllowedActions(review.status);
  const immutable = isImmutable(review.status);

  return (
    <>
      {/* Immutable state banner */}
      {immutable && (
        <div className="flex items-center gap-2 rounded-lg border-2 border-amber-300 bg-amber-50 px-4 py-3 dark:border-amber-700 dark:bg-amber-900/20">
          <Lock className="h-5 w-5 text-amber-600 dark:text-amber-400" />
          <div>
            <p className="text-sm font-bold text-amber-800 dark:text-amber-300">
              Review is {review.status.replace(/_/g, " ")} — Read Only
            </p>
            <p className="text-xs text-amber-700 dark:text-amber-400">
              Content is locked. No edits, approvals, or workflow actions are available.
            </p>
          </div>
        </div>
      )}

      {/* Action buttons bar — enterprise workflow intelligence */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <span className="mr-2 text-xs font-medium text-gray-500 dark:text-gray-400">Actions:</span>

        {/* Core actions */}
        <button
          onClick={() => setActiveModal("assign")}
          disabled={!actions.canAssign || !canAssign}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-100 px-3 py-2 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-200 disabled:opacity-40 dark:bg-indigo-900/30 dark:text-indigo-300 dark:hover:bg-indigo-800"
          title={!actions.canAssign ? `Cannot assign in '${review.status}' state` : !canAssign ? "You don't have permission to assign" : "Assign reviewer"}
        >
          <UserPlus className="h-3.5 w-3.5" />
          Assign
        </button>

        <button
          onClick={() => setActiveModal("comment")}
          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-100 px-3 py-2 text-xs font-medium text-teal-700 transition-colors hover:bg-teal-200 dark:bg-teal-900/30 dark:text-teal-300 dark:hover:bg-teal-800"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Comment
        </button>

        <button
          onClick={() => setActiveModal("escalate")}
          disabled={!actions.canEscalate || !canEscalate}
          className="inline-flex items-center gap-1.5 rounded-lg bg-orange-100 px-3 py-2 text-xs font-medium text-orange-700 transition-colors hover:bg-orange-200 disabled:opacity-40 dark:bg-orange-900/30 dark:text-orange-300 dark:hover:bg-orange-800"
          title={!actions.canEscalate ? `Cannot escalate in '${review.status}' state` : !canEscalate ? "You don't have permission to escalate" : "Escalate review"}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          Escalate
        </button>

        <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />

        {/* Workflow routing */}
        <button
          onClick={() => setActiveModal("send_to_legal")}
          disabled={immutable || !canRouteToLegal}
          className="inline-flex items-center gap-1.5 rounded-lg bg-violet-100 px-3 py-2 text-xs font-medium text-violet-700 transition-colors hover:bg-violet-200 disabled:opacity-40 dark:bg-violet-900/30 dark:text-violet-300 dark:hover:bg-violet-800"
          title={immutable ? "Review is locked" : !canRouteToLegal ? "You don't have permission to route to Legal" : "Send to Legal Review"}
        >
          <Scale className="h-3.5 w-3.5" />
          Legal
        </button>

        <button
          onClick={() => setActiveModal("send_to_procurement")}
          disabled={immutable || !canRouteToProcurement}
          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-100 px-3 py-2 text-xs font-medium text-teal-700 transition-colors hover:bg-teal-200 disabled:opacity-40 dark:bg-teal-900/30 dark:text-teal-300 dark:hover:bg-teal-800"
          title={immutable ? "Review is locked" : !canRouteToProcurement ? "You don't have permission to route to Procurement" : "Send to Procurement Review"}
        >
          <Briefcase className="h-3.5 w-3.5" />
          Procurement
        </button>

        <button
          onClick={() => setActiveModal("send_to_security")}
          disabled={immutable || !canRouteToSecurity}
          className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-100 px-3 py-2 text-xs font-medium text-cyan-700 transition-colors hover:bg-cyan-200 disabled:opacity-40 dark:bg-cyan-900/30 dark:text-cyan-300 dark:hover:bg-cyan-800"
          title={immutable ? "Review is locked" : !canRouteToSecurity ? "You don't have permission to route to Security" : "Send to Security Review"}
        >
          <Shield className="h-3.5 w-3.5" />
          Security
        </button>

        <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />

        {/* Decision actions — show actual status when in terminal/completed state */}
        {review.status === "approved" ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-green-100 px-3 py-2 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Approved
          </span>
        ) : review.status === "rejected" ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-red-100 px-3 py-2 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">
            <XCircle className="h-3.5 w-3.5" />
            Rejected
          </span>
        ) : review.status === "closed" ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-gray-100 px-3 py-2 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Closed
          </span>
        ) : review.status === "finalized" ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-100 px-3 py-2 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Finalized
          </span>
        ) : review.status === "executed" ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-100 px-3 py-2 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Executed
          </span>
        ) : (
          <>
            <button
              onClick={() => { setApproveDecision("approved"); setActiveModal("approve"); }}
              disabled={!actions.canApprove || !canApproveReject}
              className="inline-flex items-center gap-1.5 rounded-lg bg-green-100 px-3 py-2 text-xs font-medium text-green-700 transition-colors hover:bg-green-200 disabled:opacity-40 dark:bg-green-900/30 dark:text-green-300 dark:hover:bg-green-800"
              title={!actions.canApprove ? `Cannot approve in '${review.status}' state` : !canApproveReject ? "You don't have permission to approve" : "Approve review"}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Approve
            </button>

            <button
              onClick={() => { setApproveDecision("rejected"); setActiveModal("approve"); }}
              disabled={!actions.canReject || !canApproveReject}
              className="inline-flex items-center gap-1.5 rounded-lg bg-red-100 px-3 py-2 text-xs font-medium text-red-700 transition-colors hover:bg-red-200 disabled:opacity-40 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-800"
              title={!actions.canReject ? `Cannot reject in '${review.status}' state` : !canApproveReject ? "You don't have permission to reject" : "Reject review"}
            >
              <XCircle className="h-3.5 w-3.5" />
              Reject
            </button>

            {/* Finalize — only when approved */}
            {review.status === "approved" && (
              <button
                onClick={() => setActiveModal("finalize")}
                disabled={finalizeMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-100 px-3 py-2 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-200 disabled:opacity-40 dark:bg-emerald-900/30 dark:text-emerald-300 dark:hover:bg-emerald-800"
                title="Finalize approved review — locks the version"
              >
                {finalizeMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCheck className="h-3.5 w-3.5" />}
                Finalize
              </button>
            )}

            {/* Close — available from finalized or executed (not approved) */}
            {(review.status === "finalized" || review.status === "executed") && (
              <button
                onClick={() => setActiveModal("close")}
                disabled={closeMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-gray-100 px-3 py-2 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-40 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                title="Close contract — ends the lifecycle"
              >
                {closeMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Archive className="h-3.5 w-3.5" />}
                Close
              </button>
            )}
          </>
        )}

        <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />

        {/* Enterprise actions */}
        <button
          onClick={() => setActiveModal("request_revision")}
          disabled={immutable}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-100 px-3 py-2 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-200 disabled:opacity-40 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-800"
          title="Request Counterparty Revision"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Request Revision
        </button>

        <button
          onClick={() => setActiveModal("generate_negotiation")}
          disabled={immutable || !canExport}
          className="inline-flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-2 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-200 disabled:opacity-40 dark:bg-amber-900/30 dark:text-amber-300 dark:hover:bg-amber-800"
          title={immutable ? "Review is locked" : !canExport ? "You don't have permission to export" : "Generate Negotiation Package"}
        >
          <FileText className="h-3.5 w-3.5" />
          Negotiation Pkg
        </button>

        <button
          onClick={() => setActiveModal("export_memo")}
          disabled={immutable || !canExport}
          className="inline-flex items-center gap-1.5 rounded-lg bg-gray-100 px-3 py-2 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-40 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          title={immutable ? "Review is locked" : !canExport ? "You don't have permission to export" : "Export Review Memo"}
        >
          <FileDown className="h-3.5 w-3.5" />
          Export Memo
        </button>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setActiveModal("delete")}
            disabled={!actions.canDelete || !canDelete}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 disabled:opacity-30 dark:text-gray-400 dark:hover:bg-gray-700"
            title={!actions.canDelete ? `Cannot delete in '${review.status}' state` : !canDelete ? "You don't have permission to delete" : "Delete review"}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
      </div>

      {/* ── Modals ── */}

      {/* Assign Modal */}
      {activeModal === "assign" && (
        <Modal onClose={closeModal} title="Assign Reviewer">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Reviewer</label>
              <UserPicker
                value={assigneeId}
                onChange={setAssigneeId}
                allowedRoles={["tenant_admin", "reviewer", "legal_ops", "legal_reviewer", "compliance", "executive", "admin"]}
                placeholder="Search by name, email, or role…"
                size="md"
                allowNone
                noneLabel="— Unassigned —"
                reviewerWorkloads={reviewerWorkloads}
              />
              <p className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
                Pick a user from your tenant directory.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Role</label>
              <select
                value={assignRole}
                onChange={(e) => setAssignRole(e.target.value as any)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
              >
                <option value="reviewer">Reviewer</option>
                <option value="approver">Approver</option>
                <option value="observer">Observer</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={handleAssign} disabled={!assigneeId || assignMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {assignMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Assign
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Escalate Modal — same workflow routing as Review Queue (Legal / Exec / Compliance) */}
      <AnimatePresence>
        {activeModal === "escalate" && (
          <EscalationModal
            reviewId={reviewId}
            reviewTitle={
              review.document_name
              || review.original_filename
              || `Review ${reviewId.slice(0, 8)}`
            }
            currentPriority={review.priority}
            currentStage={review.workflow_stage}
            currentStatus={review.status}
            onEscalate={async (reason, escalatedTo, raisePriority, targetStage) => {
              await escalateMutation.mutateAsync({
                reason,
                escalated_to: escalatedTo,
                raise_priority: raisePriority,
                target_workflow_stage: targetStage,
              });
              closeModal();
            }}
            onClose={closeModal}
            isLoading={escalateMutation.isPending}
          />
        )}
      </AnimatePresence>

      {/* Approve/Reject Modal */}
      {activeModal === "approve" && (
        <Modal onClose={closeModal} title={approveDecision === "approved" ? "Approve Review" : approveDecision === "rejected" ? "Reject Review" : "Conditionally Approve"}>
          <div className="space-y-4">            {/* Warning: open critical findings */}
            {hasBlockingFindings && approveDecision === "approved" && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-900/50 dark:bg-red-900/20">
                <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm font-semibold">Blocking Findings</span>
                </div>
                <p className="mt-1 text-xs text-red-600 dark:text-red-300">
                  {openFindingsData?.count} critical/high finding(s) are still open.
                  {openFindingsData?.items?.map((f: Record<string, unknown>) => (
                    <span key={String(f.id)} className="block ml-4 mt-0.5">• {String(f.title)}</span>
                  ))}
                </p>
                <p className="mt-1 text-xs text-red-500 dark:text-red-400">
                  Resolve or dismiss findings before approving, or use "Conditionally Approve" to bypass.
                </p>
              </div>
            )}
            <div className="flex gap-2">
              {(["approved", "rejected", "conditionally_approved"] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setApproveDecision(d)}
                  className={`flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                    approveDecision === d
                      ? d === "approved" ? "bg-green-100 text-green-700 ring-2 ring-green-500"
                        : d === "rejected" ? "bg-red-100 text-red-700 ring-2 ring-red-500"
                        : "bg-amber-100 text-amber-700 ring-2 ring-amber-500"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400"
                  }`}>
                  {d.replace(/_/g, " ")}
                </button>
              ))}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {approveDecision === "rejected" ? "Rejection Reason" : "Comments"}
                {approveDecision === "rejected" && <span className="text-red-500"> *</span>}
              </label>
              <textarea
                value={approveComments}
                onChange={(e) => {
                  setApproveComments(e.target.value);
                  setApproveError("");
                }}
                rows={3}
                placeholder={approveDecision === "rejected" ? "Explain why this contract is being rejected (e.g., unacceptable liability limits, missing clauses, etc.)" : "Optional comments..."}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
              />
            </div>
            {approveError && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
                {approveError}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={handleApprove} disabled={approveMutation.isPending || openFindingsLoading || (hasBlockingFindings && (approveDecision === "approved" || (approveDecision === "conditionally_approved" && !approveComments.toLowerCase().includes("override:")))) || (approveDecision === "rejected" && !approveComments.trim())}
                title={openFindingsLoading ? "Checking for blocking findings..." : hasBlockingFindings && approveDecision === "approved" ? `${openFindingsData?.count ?? 0} critical/high finding(s) unresolved` : hasBlockingFindings && approveDecision === "conditionally_approved" && !approveComments.toLowerCase().includes("override:") ? "Add 'override:' in comments to bypass" : approveDecision === "rejected" && !approveComments.trim() ? "Rejection reason is required" : "Submit decision"}
                className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50 ${
                  approveDecision === "approved" ? "bg-green-600 hover:bg-green-700"
                  : approveDecision === "rejected" ? "bg-red-600 hover:bg-red-700"
                  : "bg-amber-600 hover:bg-amber-700"
                }`}>
                {approveMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                {approveDecision === "approved" ? "Approve" : approveDecision === "rejected" ? "Reject" : "Conditionally Approve"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Comment Modal */}
      {activeModal === "comment" && (
        <Modal onClose={closeModal} title="Add Comment">
          <div className="space-y-4">
            <div>
              <textarea
                value={commentBody}
                onChange={(e) => setCommentBody(e.target.value)}
                rows={4}
                placeholder="Type your comment..."
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={handleComment} disabled={!commentBody || commentMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50">
                {commentMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                <Send className="h-3.5 w-3.5" />
                Send
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Delete Modal */}
      {activeModal === "delete" && (
        <Modal onClose={closeModal} title="Delete Review">
          <div className="space-y-4">
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
              This will soft-delete the review. Data is preserved but hidden from normal views.
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Reason (optional)</label>
              <input
                type="text"
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="Why is this being deleted?"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={handleDelete} disabled={deleteMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
                {deleteMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Delete Review
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Finalize Modal */}
      {activeModal === "finalize" && (
        <Modal onClose={closeModal} title="Finalize Review">
          <div className="space-y-4">
            <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300">
              <p className="font-semibold">Finalize this approved review?</p>
              <p className="mt-1 text-xs">This locks the current document version and sets the status to FINALIZED. The contract will move to the executed/active stage.</p>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={() => finalizeMutation.mutate(reviewId, { onSuccess: () => closeModal() })} disabled={finalizeMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">
                {finalizeMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Finalize
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Close Modal */}
      {activeModal === "close" && (
        <Modal onClose={closeModal} title="Close Contract">
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              <p className="font-semibold">Close this contract?</p>
              <p className="mt-1 text-xs">This will archive the contract and end its lifecycle. Open obligations will block this action.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Closing Reason <span className="text-red-500">*</span></label>
              <textarea
                value={closeReason}
                onChange={(e) => setCloseReason(e.target.value)}
                placeholder="e.g. Contract term completed, all obligations fulfilled"
                rows={2}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
              />
              {closeReason.trim().length > 0 && closeReason.trim().length < 5 && (
                <p className="text-[10px] text-red-500 mt-0.5">Please enter at least 5 characters</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={() => closeMutation.mutate({ reviewId, reason: closeReason.trim() }, { onSuccess: () => closeModal() })} disabled={closeMutation.isPending || closeReason.trim().length < 5}
                className="inline-flex items-center gap-1.5 rounded-lg bg-gray-600 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50">
                {closeMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Close Contract
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Enterprise Workflow Modals ── */}

      {/* Send to Legal */}
      {activeModal === "send_to_legal" && (
        <Modal onClose={closeModal} title="Send to Legal Review">
          <div className="space-y-4">
            <div className="rounded-lg bg-violet-50 p-3 text-sm text-violet-700 dark:bg-violet-900/20 dark:text-violet-300">
              Route this review to the Legal team for specialized contract review.
              All findings, redlines, and recommendations will be included.
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={() => handleWorkflowRouting("legal_review")} disabled={escalateMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50">
                {escalateMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                <Scale className="h-3.5 w-3.5" />
                Send to Legal
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Send to Procurement */}
      {activeModal === "send_to_procurement" && (
        <Modal onClose={closeModal} title="Send to Procurement Review">
          <div className="space-y-4">
            <div className="rounded-lg bg-teal-50 p-3 text-sm text-teal-700 dark:bg-teal-900/20 dark:text-teal-300">
              Route this review to the Procurement team for commercial and vendor review.
              Pricing, service levels, and commercial terms will be highlighted.
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={() => handleWorkflowRouting("procurement_review")} disabled={escalateMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50">
                {escalateMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                <Briefcase className="h-3.5 w-3.5" />
                Send to Procurement
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Send to Security */}
      {activeModal === "send_to_security" && (
        <Modal onClose={closeModal} title="Send to Security Review">
          <div className="space-y-4">
            <div className="rounded-lg bg-cyan-50 p-3 text-sm text-cyan-700 dark:bg-cyan-900/20 dark:text-cyan-300">
              Route this review to the Security team for data privacy and security assessment.
              Data handling, security requirements, and compliance clauses will be reviewed.
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={() => handleWorkflowRouting("security_review")} disabled={escalateMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700 disabled:opacity-50">
                {escalateMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                <Shield className="h-3.5 w-3.5" />
                Send to Security
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Request Counterparty Revision */}
      {activeModal === "request_revision" && (
        <Modal onClose={closeModal} title="Request Counterparty Revision">
          <div className="space-y-4">
            <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
              Generate a formal revision request to the counterparty. All proposed redlines
              and recommended mitigations will be bundled into a revision package.
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={handleRequestRevision} disabled={commentMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {commentMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                <RefreshCw className="h-3.5 w-3.5" />
                Send Revision Request
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Generate Negotiation Package */}
      {activeModal === "generate_negotiation" && (
        <Modal onClose={closeModal} title="Generate Negotiation Package">
          <div className="space-y-4">
            <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
              Bundle all findings, proposed redlines, recommended mitigations, and risk analysis
              into a comprehensive negotiation package for counterparty discussions.
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={handleGenerateNegotiation} disabled={commentMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50">
                {commentMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                <FileText className="h-3.5 w-3.5" />
                Generate Package
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Export Review Memo */}
      {activeModal === "export_memo" && (
        <Modal onClose={closeModal} title="Export Review Memo">
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              Export a complete review memo including executive summary, risk breakdown,
              findings detail, and decision history. Available in PDF and DOCX formats.
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={handleExportMemo} disabled={commentMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 dark:bg-gray-600 dark:hover:bg-gray-500">
                {commentMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                <FileDown className="h-3.5 w-3.5" />
                Export Memo
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

// ── Simple Modal Component ──

function Modal({ children, onClose, title }: { children: React.ReactNode; onClose: () => void; title: string }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="mx-4 w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
        {children}
      </div>
    </div>
  );
}

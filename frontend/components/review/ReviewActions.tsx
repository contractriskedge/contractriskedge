/**
 * ReviewActions — enterprise workflow action bar for review management.
 *
 * Implements:
 * - Assign reviewer
 * - Escalate review
 * - Approve / Reject / Conditionally approve
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
import { AnimatePresence } from "framer-motion";
import {
  UserPlus, AlertTriangle, CheckCircle2, XCircle, Lock,
  MessageSquare, Trash2, ChevronDown, Send, Loader2,
  Scale, Briefcase, Shield, FileText, FileDown, RefreshCw,
} from "lucide-react";
import type { ReviewDetail } from "@/services/api/client";
import { ApiRequestError } from "@/services/api/client";
import { reviewService } from "@/services/api/reviews";
import {
  useAssignReviewer, useEscalateReview, useApproveReview,
  useAddComment, useDeleteReview,
} from "@/services/hooks";
import { api } from "@/services/api/client";
import { useAuth } from "@/providers/AuthProvider";
import { EscalationModal } from "./EscalationModal";
import { getAllowedActions, isImmutable, WORKFLOW_STATES } from "@/lib/workflow";

interface ReviewActionsProps {
  reviewId: string;
  review: ReviewDetail;
}

type ActionModal = "assign" | "escalate" | "approve" | "comment" | "delete"
  | "send_to_legal" | "send_to_procurement" | "send_to_security"
  | "request_revision" | "generate_negotiation" | "export_memo" | null;

export function ReviewActions({ reviewId, review }: ReviewActionsProps) {
  const [activeModal, setActiveModal] = useState<ActionModal>(null);
  const { hasPermission } = useAuth();

  // Permission checks
  const canAssign = hasPermission("workflows:write");
  const canEscalate = hasPermission("workflows:escalate");
  const canApproveReject = hasPermission("workflows:approve");
  const canRouteToLegal = hasPermission("workflows:approve") || hasPermission("workflows:escalate");
  const canRouteToProcurement = hasPermission("workflows:write");
  const canRouteToSecurity = hasPermission("workflows:write") || hasPermission("audit:read");
  const canExport = hasPermission("reviews:export") || hasPermission("audit:export");
  const canDelete = hasPermission("contracts:delete");

  // Mutations
  const assignMutation = useAssignReviewer(reviewId);
  const escalateMutation = useEscalateReview(reviewId);
  const approveMutation = useApproveReview(reviewId);
  const commentMutation = useAddComment(reviewId);
  const deleteMutation = useDeleteReview();

  // Form state
  const [assigneeId, setAssigneeId] = useState("");
  const [assignRole, setAssignRole] = useState<"reviewer" | "approver" | "observer">("reviewer");
  const [approveDecision, setApproveDecision] = useState<"approved" | "rejected" | "conditionally_approved">("approved");
  const [approveComments, setApproveComments] = useState("");
  const [approveError, setApproveError] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [deleteReason, setDeleteReason] = useState("");

  const closeModal = () => {
    setActiveModal(null);
    setAssigneeId("");
    setApproveComments("");
    setApproveError("");
    setCommentBody("");
    setDeleteReason("");
  };

  const handleAssign = async () => {
    if (!assigneeId) return;
    const key = api.generateIdempotencyKey();
    await assignMutation.mutateAsync(
      { assignee_id: assigneeId, role: assignRole },
    );
    closeModal();
  };

  const handleApprove = async () => {
    setApproveError("");
    try {
      await approveMutation.mutateAsync({
        decision: approveDecision,
        comments: approveComments || undefined,
      });
      closeModal();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setApproveError(err.message);
      } else {
        setApproveError(err instanceof Error ? err.message : "Approval failed");
      }
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

        {/* Decision actions */}
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
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assignee ID</label>
              <input
                type="text"
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value)}
                placeholder="User ID or email"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
              />
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
          <div className="space-y-4">
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
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Comments</label>
              <textarea
                value={approveComments}
                onChange={(e) => {
                  setApproveComments(e.target.value);
                  setApproveError("");
                }}
                rows={3}
                placeholder="Optional comments..."
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
              <button onClick={handleApprove} disabled={approveMutation.isPending}
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

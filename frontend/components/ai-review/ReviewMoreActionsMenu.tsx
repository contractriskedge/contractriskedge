/**
 * ReviewMoreActionsMenu — dropdown workflow & export actions for the AI review workspace.
 */

"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import {
  UserPlus, AlertTriangle, FileText, Shield, Lock, ExternalLink,
  GitCompare, BarChart3, Download, ChevronDown, Loader2, Send,
} from "lucide-react";
import {
  locateClause,
  requestLocateRedlineSource,
  requestShowDocumentPanel,
} from "@/lib/highlightClause";
import { reviewService } from "@/services/api/reviews";
import {
  useAssignReviewer,
  useEscalateReview,
  useAddComment,
} from "@/services/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { EscalationModal } from "@/components/review/EscalationModal";
import { UserPicker } from "@/components/shared/UserPicker";
import {
  getEscalationBlockReason,
  isImmutable,
} from "@/lib/workflow";
import { platformKeys } from "./hooks";
import type { Finding, ReviewSummary } from "./types";
import type { ReviewSection } from "./types";

type ActionModal =
  | "assign"
  | "escalate"
  | "business_review"
  | "procurement_review"
  | "security_review"
  | "export_package"
  | "negotiation_package"
  | "executive_summary"
  | null;

interface ReviewMoreActionsMenuProps {
  review: ReviewSummary;
  selectedFindingId: string | null;
  findings: Finding[];
  /** Current active section so locate is context-sensitive. */
  activeSection?: ReviewSection;
  onLocateClause?: (findingId: string) => void;
  onNavigateSection?: (section: ReviewSection) => void;
}

function ActionModalShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="mx-4 w-full max-w-md rounded-xl bg-white p-4 shadow-xl dark:bg-navy-800"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-3 text-sm font-semibold text-navy-900 dark:text-white">{title}</h3>
        {children}
      </div>
    </div>
  );
}

export function ReviewMoreActionsMenu({
  review,
  selectedFindingId,
  findings,
  activeSection = "findings",
  onLocateClause,
  onNavigateSection,
}: ReviewMoreActionsMenuProps) {
  const reviewId = review.review_id;
  const queryClient = useQueryClient();
  const menuRef = useRef<HTMLDivElement>(null);

  const [open, setOpen] = useState(false);
  const [activeModal, setActiveModal] = useState<ActionModal>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const [assigneeId, setAssigneeId] = useState("");
  const [assignRole, setAssignRole] = useState<"reviewer" | "approver" | "observer">("reviewer");

  const assignMutation = useAssignReviewer(reviewId);
  const escalateMutation = useEscalateReview(reviewId);
  const commentMutation = useAddComment(reviewId);

  const closeMenu = useCallback(() => setOpen(false), []);

  const closeModal = useCallback(() => {
    setActiveModal(null);
    setAssigneeId("");
    setActionError(null);
  }, []);

  const invalidateReviewData = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: platformKeys.all });
  }, [queryClient]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeMenu();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, closeMenu]);

  const runWorkflowRouting = async (targetStage: string, label: string) => {
    if (reviewImmutable) {
      setActionError(
        escalationBlockReason ?? `Cannot route review in '${reviewStatus}' state`,
      );
      return;
    }
    setBusyAction(label);
    setActionError(null);
    try {
      await escalateMutation.mutateAsync({
        reason: `Routing to ${label}`,
        escalated_to: targetStage,
        raise_priority: false,
        target_workflow_stage: targetStage,
      });
      invalidateReviewData();
      closeModal();
      closeMenu();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Workflow routing failed");
    } finally {
      setBusyAction(null);
    }
  };

  const handleAssign = async () => {
    if (!assigneeId.trim()) return;
    setBusyAction("assign");
    setActionError(null);
    try {
      await assignMutation.mutateAsync({
        assignee_id: assigneeId.trim(),
        role: assignRole,
      });
      invalidateReviewData();
      closeModal();
      closeMenu();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Assign failed");
    } finally {
      setBusyAction(null);
    }
  };

  const handleLocateCurrentClause = () => {
    if (activeSection === "redline") {
      setActionError(null);
      requestShowDocumentPanel();
      requestLocateRedlineSource();
      closeMenu();
      return;
    }

    if (activeSection === "recommendations") {
      // When in Recommendations tab, find a recommendation-linked finding
      const recFinding = findings.find((f) => f.page_numbers?.length);
      if (recFinding) {
        locateClause({
          page: recFinding.page_numbers[0] || 1,
          findingId: recFinding.finding_id,
          clauseText: recFinding.clause_text || recFinding.description || undefined,
        });
        onLocateClause?.(recFinding.finding_id);
        closeMenu();
        return;
      }
    }

    // Default: Findings tab — locate the selected finding, or first open finding
    const finding =
      (selectedFindingId ? findings.find((f) => f.finding_id === selectedFindingId) : null) ??
      findings.find((f) => f.status === "open") ??
      findings[0];

    if (!finding) {
      setActionError("No finding available to locate in the document.");
      return;
    }

    setActionError(null);
    locateClause({
      page: finding.page_numbers[0] || 1,
      findingId: finding.finding_id,
      clauseText: finding.clause_text || finding.description || undefined,
    });
    onLocateClause?.(finding.finding_id);
    closeMenu();
  };

  const handleExportPackage = async () => {
    setBusyAction("export");
    setActionError(null);
    try {
      await reviewService.exportReviewAudit(reviewId);
      closeMenu();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusyAction(null);
    }
  };

  const handleNegotiationPackage = async () => {
    setBusyAction("negotiation");
    setActionError(null);
    try {
      await reviewService.exportNegotiationPackage(reviewId);
      await commentMutation.mutateAsync({
        body: "**Negotiation Package Generated** — Findings, redlines, and recommendations bundled for negotiation.",
      });
      invalidateReviewData();
      closeMenu();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Negotiation package export failed");
    } finally {
      setBusyAction(null);
    }
  };

  const handleExecutiveSummary = async () => {
    setBusyAction("executive");
    setActionError(null);
    try {
      await reviewService.exportExecutiveSummary(reviewId);
      await commentMutation.mutateAsync({
        body: "**Executive Summary Generated** — Review memo exported for leadership distribution.",
      });
      invalidateReviewData();
      closeMenu();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Executive summary export failed");
    } finally {
      setBusyAction(null);
    }
  };

  const handleDownloadRedline = async () => {
    setBusyAction("redline");
    setActionError(null);
    try {
      let versionId = "latest";
      try {
        const versions = await reviewService.listVersions(reviewId);
        if (Array.isArray(versions) && versions.length > 0) {
          const latest = versions[versions.length - 1] as { version_id?: string; id?: string };
          versionId = latest.version_id ?? latest.id ?? versionId;
        }
      } catch {
        // Fall back to "latest" when version list is unavailable
      }
      await reviewService.exportTrackedChanges(reviewId, versionId);
      closeMenu();
    } catch (err) {
      onNavigateSection?.("redline");
      setActionError(
        err instanceof Error
          ? `${err.message} — opened Redline tab.`
          : "Redline download failed — opened Redline tab.",
      );
    } finally {
      setBusyAction(null);
    }
  };

  const menuItems: Array<{
    id: string;
    label: string;
    icon: React.ElementType;
    className: string;
    onClick: () => void;
  }> = [
    {
      id: "assign",
      label: "Assign",
      icon: UserPlus,
      className: "text-gray-700 dark:text-gray-200",
      onClick: () => {
        closeMenu();
        setActiveModal("assign");
      },
    },
    {
      id: "escalate",
      label: "Escalate",
      icon: AlertTriangle,
      className: "text-orange-600",
      onClick: () => {
        if (!canEscalateWorkflow) {
          setActionError(escalateTitle);
          return;
        }
        closeMenu();
        setActiveModal("escalate");
      },
    },
    {
      id: "business",
      label: "Business Review",
      icon: FileText,
      className: "text-blue-600",
      onClick: () => {
        closeMenu();
        setActiveModal("business_review");
      },
    },
    {
      id: "procurement",
      label: "Procurement Review",
      icon: Shield,
      className: "text-purple-600",
      onClick: () => {
        closeMenu();
        setActiveModal("procurement_review");
      },
    },
    {
      id: "security",
      label: "Security Review",
      icon: Lock,
      className: "text-cyan-600",
      onClick: () => {
        closeMenu();
        setActiveModal("security_review");
      },
    },
    {
      id: "locate",
      label: "View Source Location",
      icon: ExternalLink,
      className: "text-navy-600",
      onClick: handleLocateCurrentClause,
    },
    {
      id: "export",
      label: "Export Review Package",
      icon: FileText,
      className: "text-emerald-600",
      onClick: () => void handleExportPackage(),
    },
    {
      id: "audit",
      label: "Export Audit Package",
      icon: Shield,
      className: "text-red-600",
      onClick: () => void handleExportPackage(),
    },
    {
      id: "negotiation",
      label: "Create Negotiation Package",
      icon: GitCompare,
      className: "text-amber-600",
      onClick: () => void handleNegotiationPackage(),
    },
    {
      id: "executive",
      label: "Generate Executive Summary",
      icon: BarChart3,
      className: "text-indigo-600",
      onClick: () => void handleExecutiveSummary(),
    },
    {
      id: "redline",
      label: "Download Redline",
      icon: Download,
      className: "text-amber-600",
      onClick: () => void handleDownloadRedline(),
    },
  ];

  // Workflow-state guard: disable escalation when the review is in a
  // terminal/locked state or already escalated. Mirrors the matrix in
  // `lib/workflow.ts#getAllowedActions`.
  const reviewStatus = review.status;
  const reviewImmutable = isImmutable(reviewStatus);
  const escalationBlockReason = getEscalationBlockReason(reviewStatus);
  const canEscalateWorkflow = !reviewImmutable && escalationBlockReason === null;
  const escalateTitle = !canEscalateWorkflow
    ? (escalationBlockReason ?? `Cannot escalate in '${reviewStatus}' state`)
    : "Escalate review";

  const isBusy = Boolean(busyAction) || assignMutation.isPending || escalateMutation.isPending;

  return (
    <>
      <div className="relative" ref={menuRef}>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setOpen((prev) => !prev);
            setActionError(null);
          }}
          className="flex items-center gap-1 px-1.5 py-1 text-[9px] font-medium rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-600 dark:text-gray-300 transition-colors"
          aria-expanded={open}
          aria-haspopup="menu"
        >
          More Actions <ChevronDown className="w-2.5 h-2.5" />
        </button>

        <AnimatePresence>
          {open && (
            <>
              <button
                type="button"
                className="fixed inset-0 z-40 cursor-default"
                aria-label="Close menu"
                onClick={closeMenu}
              />
              <div
                role="menu"
                className="absolute right-0 top-full mt-1 z-50 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg shadow-xl py-1 w-48"
                onClick={(e) => e.stopPropagation()}
              >
                {menuItems.map((item, index) => {
                  const Icon = item.icon;
                  const showDividerBefore = index === 1 || index === 5 || index === 9;
                  // The Escalate menu item is also blocked by the workflow
                  // state guard (immutable status or already-escalated).
                  const isItemBlocked =
                    item.id === "escalate" && !canEscalateWorkflow;
                  return (
                    <React.Fragment key={item.id}>
                      {showDividerBefore && (
                        <div className="border-t border-gray-100 dark:border-navy-700 my-1" role="separator" />
                      )}
                      <button
                        type="button"
                        role="menuitem"
                        disabled={
                          (isBusy && item.id !== "locate" && item.id !== "redline") ||
                          isItemBlocked
                        }
                        title={isItemBlocked ? escalateTitle : undefined}
                        onClick={(e) => {
                          e.stopPropagation();
                          item.onClick();
                        }}
                        className={`w-full text-left px-3 py-1.5 text-[9px] hover:bg-gray-50 dark:hover:bg-navy-700 flex items-center gap-1.5 disabled:opacity-50 ${item.className}`}
                      >
                        {busyAction === item.id ? (
                          <Loader2 className="w-3 h-3 animate-spin flex-shrink-0" />
                        ) : (
                          <Icon className="w-3 h-3 flex-shrink-0" />
                        )}
                        {item.label}
                      </button>
                    </React.Fragment>
                  );
                })}
                {(actionError || busyAction) && !activeModal && (
                  <p className="px-3 py-1.5 text-[8px] border-t border-gray-100 dark:border-navy-700 text-gray-500">
                    {busyAction ? (
                      <span className="inline-flex items-center gap-1">
                        <Loader2 className="w-2.5 h-2.5 animate-spin" /> Working…
                      </span>
                    ) : (
                      <span className="text-red-600">{actionError}</span>
                    )}
                  </p>
                )}
              </div>
            </>
          )}
        </AnimatePresence>
      </div>

      {activeModal === "assign" && (
        <ActionModalShell title="Assign Reviewer" onClose={closeModal}>
          <div className="space-y-3">
            <div>
              <label className="block text-[10px] font-medium text-gray-600 dark:text-gray-300 mb-1">
                Reviewer
              </label>
              <UserPicker
                value={assigneeId}
                onChange={setAssigneeId}
                allowedRoles={["tenant_admin", "reviewer", "legal_ops", "compliance", "executive", "admin"]}
                placeholder="Search by name, email, or role…"
                size="sm"
                allowNone
                noneLabel="— Unassigned —"
              />
            </div>
            <div>
              <label className="block text-[10px] font-medium text-gray-600 dark:text-gray-300 mb-1">Role</label>
              <select
                value={assignRole}
                onChange={(e) => setAssignRole(e.target.value as typeof assignRole)}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs dark:border-navy-600 dark:bg-navy-700 dark:text-white"
              >
                <option value="reviewer">Reviewer</option>
                <option value="approver">Approver</option>
                <option value="observer">Observer</option>
              </select>
            </div>
            {actionError && <p className="text-[10px] text-red-600">{actionError}</p>}
            <div className="flex justify-end gap-2">
              <button type="button" onClick={closeModal} className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded">
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAssign}
                disabled={!assigneeId.trim() || assignMutation.isPending}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded bg-navy-600 text-white hover:bg-navy-700 disabled:opacity-50"
              >
                {assignMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                Assign
              </button>
            </div>
          </div>
        </ActionModalShell>
      )}

      <AnimatePresence>
        {activeModal === "escalate" && (
          <EscalationModal
            reviewId={reviewId}
            reviewTitle={review.contract_name}
            currentPriority={review.priority}
            currentStage={review.workflow_stage}
            currentStatus={reviewStatus}
            onEscalate={async (reason, escalatedTo, raisePriority, targetStage) => {
              await escalateMutation.mutateAsync({
                reason,
                escalated_to: escalatedTo,
                raise_priority: raisePriority,
                target_workflow_stage: targetStage,
              });
              invalidateReviewData();
              closeModal();
            }}
            onClose={closeModal}
            isLoading={escalateMutation.isPending}
          />
        )}
      </AnimatePresence>

      {activeModal === "business_review" && (
        <ActionModalShell title="Send to Business Review" onClose={closeModal}>
          <p className="text-[11px] text-gray-600 dark:text-gray-300 mb-3">
            Route this review to business leadership for commercial and strategic approval.
          </p>
          {actionError && <p className="text-[10px] text-red-600 mb-2">{actionError}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={closeModal} className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => runWorkflowRouting("exec_approval", "Business Review")}
              disabled={escalateMutation.isPending}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {escalateMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
              <Send className="w-3 h-3" /> Send to Business
            </button>
          </div>
        </ActionModalShell>
      )}

      {activeModal === "procurement_review" && (
        <ActionModalShell title="Send to Procurement Review" onClose={closeModal}>
          <p className="text-[11px] text-gray-600 dark:text-gray-300 mb-3">
            Route to procurement for commercial terms, pricing, and vendor assessment.
          </p>
          {actionError && <p className="text-[10px] text-red-600 mb-2">{actionError}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={closeModal} className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => runWorkflowRouting("procurement_review", "Procurement Review")}
              disabled={escalateMutation.isPending}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
            >
              {escalateMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
              <Send className="w-3 h-3" /> Send to Procurement
            </button>
          </div>
        </ActionModalShell>
      )}

      {activeModal === "security_review" && (
        <ActionModalShell title="Send to Security Review" onClose={closeModal}>
          <p className="text-[11px] text-gray-600 dark:text-gray-300 mb-3">
            Route to security for data privacy, access controls, and compliance review.
          </p>
          {actionError && <p className="text-[10px] text-red-600 mb-2">{actionError}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={closeModal} className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded">
              Cancel
            </button>
            <button
              type="button"
              onClick={() => runWorkflowRouting("security_review", "Security Review")}
              disabled={escalateMutation.isPending}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-50"
            >
              {escalateMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
              <Send className="w-3 h-3" /> Send to Security
            </button>
          </div>
        </ActionModalShell>
      )}
    </>
  );
}

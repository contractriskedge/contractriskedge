/**
 * ReviewQueue — enterprise operational review queue.
 *
 * Full-width enterprise layout consistent with AI Review Workspace.
 * Inspired by ServiceNow, Jira, Relativity, Microsoft Purview.
 *
 * Features:
 * - Workload metrics bar (full-width KPI strip)
 * - Multi-select with bulk actions (Assign / Escalate / Approve / Export)
 * - Queue filter tabs (All / My / Legal / Executive / Compliance / Escalated / Overdue)
 * - Search and status filtering
 * - Sortable columns with sticky header
 * - SLA status with color-coded badges
 * - Row-level actions (Assign / Approve / Escalate / Open)
 * - Optimistic UI updates
 * - Assign modal with reviewer search
 * - Approval and escalation modals
 * - Overdue row indicators
 */

"use client";

import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText, AlertTriangle, Clock, ArrowUpDown, Lock,
  Search, Check, X, Loader2, UserPlus, ArrowUpRight, Archive,
  CheckSquare, Square, ChevronDown, Eye, ThumbsUp, ThumbsDown, Download,
  ListChecks, Brain, Filter, Star, RefreshCw, CheckCircle2,
} from "lucide-react";
import { reviewService } from "@/services/api/reviews";
import { obligationsService } from "@/services/api/obligations";
import { api } from "@/services/api/client";
import type { ReviewDetail, WorkloadMetrics } from "@/services/api/client";
import { ApprovalModal } from "./ApprovalModal";
import { EscalationModal } from "./EscalationModal";
import { getAllowedActions, isImmutable, getStatusLabel } from "@/lib/workflow";
import { PageHeader } from "@/components/shared/PageHeader";
import { UserPicker } from "@/components/shared/UserPicker";
import { useAuth } from "@/components/auth/AuthProvider";
import { useFavorites } from "@/hooks/useFavorites";
import { useReviewerWorkloads } from "@/components/ai-review/hooks";

// ── Hooks ───────────────────────────────────────────────────────

function useReviewsList(assignedTo?: string) {
  const params: Record<string, unknown> = { page_size: 100 };
  if (assignedTo) {
    params.assigned_to = assignedTo;
  }
  return useQuery({
    queryKey: ["reviews", "queue", assignedTo || "all"],
    queryFn: () => reviewService.list(params as any),
    staleTime: 30_000,
    refetchInterval: 60_000,
    notifyOnChangeProps: ["data"],
  });
}

function useMyReviews() {
  return useQuery({
    queryKey: ["reviews", "my-work"],
    queryFn: () => reviewService.getMyWork(),
    staleTime: 30_000,
    refetchInterval: 60_000,
    notifyOnChangeProps: ["data"],
  });
}

function useWorkloadMetrics() {
  return useQuery({
    queryKey: ["reviews", "workload"],
    queryFn: () => reviewService.getWorkloadMetrics(),
    staleTime: 15_000,
    refetchInterval: 30_000,
    notifyOnChangeProps: ["data"],
  });
}

// ── Helpers ─────────────────────────────────────────────────────

const riskColor = (score: number | null | undefined): string => {
  if (score == null) return "bg-gray-100 text-gray-600";
  if (score >= 0.7) return "bg-red-100 text-red-700";
  if (score >= 0.5) return "bg-orange-100 text-orange-700";
  if (score >= 0.3) return "bg-amber-100 text-amber-700";
  return "bg-green-100 text-green-700";
};

const statusColor = (status: string): string => {
  const colors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-600",
    ai_analyzed: "bg-blue-100 text-blue-700",
    under_review: "bg-purple-100 text-purple-700",
    legal_review: "bg-violet-100 text-violet-700",
    procurement_review: "bg-teal-100 text-teal-700",
    security_review: "bg-cyan-100 text-cyan-700",
    escalated: "bg-orange-100 text-orange-700",
    approved: "bg-green-100 text-green-700",
    negotiation_sent: "bg-emerald-100 text-emerald-700",
    executed: "bg-emerald-100 text-emerald-700",
    archived: "bg-gray-100 text-gray-500",
  };
  return colors[status] || "bg-gray-100 text-gray-600";
};

const slaColor = (status: string): string => {
  const colors: Record<string, string> = {
    critical_overdue: "bg-red-100 text-red-700",
    overdue: "bg-red-100 text-red-700",
    warning: "bg-amber-100 text-amber-700",
    on_track: "bg-green-100 text-green-700",
    done: "bg-gray-100 text-gray-500",
  };
  return colors[status] || "bg-gray-100 text-gray-500";
};

const stageLabel = (status: string, stage?: string | null): string => {
  if (stage) return stage.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const stages: Record<string, string> = {
    draft: "Ingestion",
    ai_analyzed: "AI Review",
    under_review: "Initial Review",
    legal_review: "Legal Review",
    procurement_review: "Procurement",
    security_review: "Security",
    escalated: "Escalated",
    approved: "Approved",
    negotiation_sent: "Negotiation",
    executed: "Executed",
    rejected: "Rejected",
    closed: "Archived",
  };
  return stages[status] || status.replace(/_/g, " ");
};

/**
 * Transform raw document name / filename into a business-friendly contract title.
 *
 * Examples:
 *   "CONTRACT_03_SaaS_HighRisk_2026.pdf" → "SaaS Agreement"
 *   "MSA_Acme_Corp_FINAL.docx"          → "Master Services Agreement – Acme Corp"
 *   "NDA_DataSync_Partners_v2.pdf"      → "Non-Disclosure Agreement – DataSync Partners"
 *   "review_abc123"                      → "Contract Review"
 *
 * Falls back to a formatted version of the original filename if no pattern matches.
 */
function formatContractTitle(review: ReviewDetail): string {
  const name = review.document_name || review.original_filename || "";
  if (!name || name.startsWith("Review ")) return "Contract Review";

  // Remove file extension
  const clean = name.replace(/\.(pdf|docx?|xlsx?|txt)$/i, "");

  // Pattern: TYPE_Vendor_Description or TYPE - Vendor
  const typeMap: Record<string, string> = {
    msa: "Master Services Agreement",
    sow: "Statement of Work",
    nda: "Non-Disclosure Agreement",
    dpa: "Data Processing Agreement",
    baa: "Business Associate Agreement",
    sla: "Service Level Agreement",
    saas: "SaaS Agreement",
    license: "Software License Agreement",
    consulting: "Consulting Services Agreement",
    supply: "Supply Agreement",
    distribution: "Distribution Agreement",
    employment: "Employment Agreement",
    lease: "Lease Agreement",
    indemnity: "Indemnity Agreement",
    settlement: "Settlement Agreement",
    amendment: "Contract Amendment",
    addendum: "Contract Addendum",
    renewal: "Renewal Agreement",
    termination: "Termination Agreement",
    services: "Services Agreement",
    partnership: "Partnership Agreement",
    sponsorship: "Sponsorship Agreement",
    franchise: "Franchise Agreement",
    loan: "Loan Agreement",
    credit: "Credit Agreement",
    procurement: "Procurement Agreement",
    outsourcing: "Outsourcing Agreement",
    confidentiality: "Confidentiality Agreement",
    non_disclosure: "Non-Disclosure Agreement",
    non_compete: "Non-Compete Agreement",
    construction: "Construction Contract",
    real_estate: "Real Estate Contract",
    insurance: "Insurance Policy",
    warranty: "Warranty Agreement",
    support: "Support Agreement",
    maintenance: "Maintenance Agreement",
    hosting: "Hosting Agreement",
    cloud: "Cloud Services Agreement",
    professional: "Professional Services Agreement",
    statement_of_work: "Statement of Work",
    master: "Master Services Agreement",
  };

  // Try to extract type and vendor from common patterns
  // Pattern 1: "TYPE_VENDOR_..." or "TYPE-VENDOR-..."
  const parts = clean.split(/[_\-]+/);
  const typeKey = parts[0]?.toLowerCase();
  const typeLabel = typeMap[typeKey];

  if (typeLabel) {
    // Try to find a vendor name in the remaining parts
    const vendorPart = parts.slice(1).filter(p => !/^\d/.test(p) && !/v\d+$/i.test(p) && !/final/i.test(p) && !/draft/i.test(p) && !/revised/i.test(p)).join(" ");
    if (vendorPart) {
      return `${typeLabel} – ${vendorPart}`;
    }
    return typeLabel;
  }

  // Pattern 2: Contains known type keywords
  for (const [key, label] of Object.entries(typeMap)) {
    if (clean.toLowerCase().includes(key)) {
      return label;
    }
  }

  // Fallback: clean up the raw name
  return clean
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/\.(pdf|docx?|xlsx?|txt)$/i, "")
    .trim() || "Contract Review";
}

function formatSLA(review: ReviewDetail): { label: string; status: string } {
  if (review.status === "approved" || review.status === "closed" || review.status === "rejected" || review.status === "archived") {
    return { label: "—", status: "done" };
  }
  if (review.sla_status === "overdue" || review.sla_status === "critical_overdue") {
    const h = Math.round(review.overdue_hours);
    return { label: `${h}h overdue`, status: "overdue" };
  }
  const dueAt = review.sla_due_at || review.sla_deadline;
  if (dueAt) {
    const deadline = new Date(dueAt).getTime();
    const now = Date.now();
    const diff = deadline - now;
    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    if (hours < 1 && hours >= 0) return { label: `${mins}m`, status: "warning" };
    if (hours < 24) return { label: `${hours}h`, status: "on_track" };
    return { label: `${Math.floor(hours / 24)}d`, status: "on_track" };
  }
  return { label: "—", status: "none" };
}

interface ReviewerOption {
  user_id: string;
  name: string;
}

// ── Assign Modal (DB-backed via UserPicker) ─────────────────────

function AssignModal({
  reviewId,
  onClose,
  onAssign,
}: {
  reviewId: string;
  onClose: () => void;
  onAssign: (assigneeId: string, assigneeName: string) => void;
}) {
  const [selected, setSelected] = useState<{ id: string; name: string } | null>(null);

  // Pull per-reviewer workload from the shared hook so the picker can
  // surface each user's active-review count + workload %.
  // The hook hits the real /reviews/reviewers/workload endpoint and falls
  // back to a cached query for any other consumers.
  const { data: reviewerWorkloads = [] } = useReviewerWorkloads();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-white rounded-xl shadow-xl border border-gray-200 w-96 overflow-visible"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-navy-900">Assign Reviewer</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-3 space-y-2 overflow-visible">
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            Reviewer
          </label>
          <div className="relative z-[100] overflow-visible">
          <UserPicker
            value={selected?.id || ""}
            onChange={(id) => {
              // Synchronised with onSelectUser below — keep id-only state
              // in sync here so the picker stays controlled even when
              // onSelectUser has not fired yet.
              if (!id) {
                setSelected(null);
                return;
              }
              setSelected({ id, name: "" });
            }}
            onSelectUser={(user) => {
              if (!user) {
                setSelected(null);
              } else {
                setSelected({ id: user.user_id, name: user.name });
              }
            }}
            allowedRoles={["tenant_admin", "reviewer", "legal_ops", "compliance", "executive", "admin"]}
            placeholder="Search by name, email, or role…"
            reviewerWorkloads={reviewerWorkloads}
            allowNone
            noneLabel="— Unassigned —"
            size="sm"
          />
          </div>
          <p className="text-[10px] text-gray-500 leading-relaxed pt-1">
            Pick a user from your tenant directory. The list shows each user's
            active-review workload to help balance assignments.
          </p>
        </div>
        <div className="px-3 py-2 border-t border-gray-100 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-[10px] font-medium text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => selected && onAssign(selected.id, selected.name)}
            disabled={!selected}
            className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Assign
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Component ────────────────────────────────────────────────────

interface ReviewQueueProps {
  onReviewSelect?: (reviewId: string) => void;
  maxItems?: number;
}

export function ReviewQueue({ onReviewSelect, maxItems }: ReviewQueueProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const favorites = useFavorites(user?.tenant_id, user?.sub);
  const [queueFilter, setQueueFilter] = useState<string>("all");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const isMyReviews = queueFilter === "my";

  const { data, isLoading } = useReviewsList();
  const { data: metrics } = useWorkloadMetrics();

  // Seed localStorage favorites from backend data on load
  const reviews = data?.data ?? [];
  const seeded = useRef(false);
  useEffect(() => {
    if (!reviews.length || seeded.current) return;
    seeded.current = true;
    for (const r of reviews) {
      if (r.is_favorite) {
        favorites.add(r.review_id);
      }
    }
  }, [reviews, favorites]);

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [stageFilter, setStageFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<
    | "risk_score"
    | "created_at"
    | "updated_at"
    | "status"
    | "priority"
    | "assigned_to"
    | "sla"
  >("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [assignTarget, setAssignTarget] = useState<string | null>(null);
  const [assigningRowId, setAssigningRowId] = useState<string | null>(null);
  const [assigningRowIds, setAssigningRowIds] = useState<Set<string>>(new Set());
  const [approvalTarget, setApprovalTarget] = useState<ReviewDetail | null>(null);
  const [escalationTarget, setEscalationTarget] = useState<ReviewDetail | null>(null);
  const [closeTarget, setCloseTarget] = useState<{ id: string; name: string } | null>(null);
  const [closeReason, setCloseReason] = useState("");
  const [bulkAction, setBulkAction] = useState<string>("");
  const [openObligationCounts, setOpenObligationCounts] = useState<Record<string, number>>({});
  const [fetchingObligations, setFetchingObligations] = useState(false);

  // Fetch open obligation counts when approval modal is triggered
  useEffect(() => {
    if (!approvalTarget || fetchingObligations) return;
    const reviewId = approvalTarget.review_id;
    if (openObligationCounts[reviewId] !== undefined) return;
    setFetchingObligations(true);
    obligationsService.getByContract(reviewId).then((res) => {
      setOpenObligationCounts(prev => ({ ...prev, [reviewId]: (res as { open?: number }).open ?? 0 }));
    }).catch(() => {
      setOpenObligationCounts(prev => ({ ...prev, [reviewId]: 0 }));
    }).finally(() => {
      setFetchingObligations(false);
    });
  }, [approvalTarget, openObligationCounts, fetchingObligations]);

  // ── Mutations ──

  const assignMut = useMutation({
    mutationFn: ({ reviewId, assigneeId }: { reviewId: string; assigneeId: string; assigneeName: string }) =>
      reviewService.assign(reviewId, { assignee_id: assigneeId }),
    onMutate: async ({ reviewId, assigneeId, assigneeName }) => {
      setAssigningRowId(reviewId);
      await queryClient.cancelQueries({ queryKey: ["reviews", "queue"] });
      // Get all matching queue queries (e.g. ["reviews", "queue", "all"], ["reviews", "queue", "user@x"])
      const queueQueries = queryClient.getQueriesData<{ data: ReviewDetail[] }>({
        queryKey: ["reviews", "queue"],
        exact: false,
      });
      for (const [queryKey, previous] of queueQueries) {
        if (previous) {
          queryClient.setQueryData(queryKey, {
            ...previous,
            data: previous.data.map((review) => {
              if (review.review_id !== reviewId) return review;
              const optimisticallyAssigned =
                review.status === "ai_analyzed" || review.status === "draft";
              return {
                ...review,
                assigned_to: assigneeId,
                assigned_to_name: assigneeName || review.assigned_to_name,
                ...(optimisticallyAssigned
                  ? { status: "in_review", workflow_stage: "reviewer" }
                  : {}),
              };
            }),
          });
        }
      }
      return { previous: queueQueries };
    },
    onSuccess: (response, { reviewId }) => {
      // The server response includes the canonical review object with
      // assigned_to_name resolved from admin_users. Replace the cached row
      // so the optimistic guess is overwritten with the authoritative data.
      const updatedReview = (response as { review?: ReviewDetail } | undefined)?.review;
      if (updatedReview) {
        const queueQueries = queryClient.getQueriesData<{ data: ReviewDetail[] }>({
          queryKey: ["reviews", "queue"],
          exact: false,
        });
        for (const [queryKey] of queueQueries) {
          queryClient.setQueryData<{ data: ReviewDetail[] }>(
            queryKey,
            (prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                data: prev.data.map((r) =>
                  r.review_id === reviewId ? { ...r, ...updatedReview } : r
                ),
              };
            }
          );
        }
      }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        for (const [queryKey, previous] of context.previous) {
          if (previous) {
            queryClient.setQueryData(queryKey, previous);
          }
        }
      }
    },
    onSettled: () => {
      // Invalidate all queue queries so any filtered views also refresh
      queryClient.invalidateQueries({ queryKey: ["reviews", "queue"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "metrics"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "my-work"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "detail"] });
      setAssignTarget(null);
      setAssigningRowId(null);
    },
  });

  // ── Approve / Reject Mutations ──

  const approveMut = useMutation({
    mutationFn: ({ reviewId, decision, comment, conditions }: {
      reviewId: string; decision: string; comment: string; conditions?: Record<string, unknown>;
    }) =>
      reviewService.approve(reviewId, { decision: decision as "approved" | "rejected" | "conditionally_approved", comments: comment, conditions }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      setApprovalTarget(null);
    },
  });

  const rejectMut = useMutation({
    mutationFn: ({ reviewId, comment, category, severity }: { reviewId: string; comment: string; category?: string; severity?: string }) =>
      reviewService.approve(reviewId, {
        decision: "rejected",
        comments: comment,
        conditions: { category, severity },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      setApprovalTarget(null);
    },
  });

  // ── Close Mutation ──

  const closeMut = useMutation({
    mutationFn: ({ reviewId, reason }: { reviewId: string; reason?: string }) =>
      reviewService.updateStatus(reviewId, "closed", reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
      setCloseTarget(null);
    },
  });

  // ── Finalize Mutation ──

  const finalizeMut = useMutation({
    mutationFn: (reviewId: string) =>
      reviewService.finalize(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
    },
  });

  const handleCloseReview = (reviewId: string, name: string) => {
    setCloseTarget({ id: reviewId, name });
    setCloseReason("");
  };

  // ── Escalate Mutation ──

  const escalateMut = useMutation({
    mutationFn: ({ reviewId, reason, escalatedTo, raisePriority, targetStage }: {
      reviewId: string; reason: string; escalatedTo?: string; raisePriority?: boolean; targetStage?: string;
    }) =>
      reviewService.escalate(reviewId, { reason, escalated_to: escalatedTo, raise_priority: raisePriority, target_workflow_stage: targetStage }),
    onSuccess: () => {
      // Invalidate all review list queries so every queue tab refreshes
      queryClient.invalidateQueries({ queryKey: ["reviews", "queue"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "my-work"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "metrics"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "detail"] });
      setEscalationTarget(null);
    },
  });

  const bulkAssignMut = useMutation({
    mutationFn: ({ ids, assigneeId }: { ids: string[]; assigneeId: string; assigneeName: string }) =>
      reviewService.bulkAssign({ review_ids: ids, assignee_id: assigneeId }),
    onMutate: async ({ ids, assigneeId, assigneeName }) => {
      // Track the in-flight rows so the Assigned cells show a spinner
      // and the row dims, giving the user immediate feedback that the
      // assignment is being persisted.
      setAssigningRowIds(new Set(ids));
      await queryClient.cancelQueries({ queryKey: ["reviews", "queue"] });
      const queueQueries = queryClient.getQueriesData<{ data: ReviewDetail[] }>({
        queryKey: ["reviews", "queue"],
        exact: false,
      });
      const idSet = new Set(ids);
      for (const [queryKey, previous] of queueQueries) {
        if (previous) {
          queryClient.setQueryData(queryKey, {
            ...previous,
            data: previous.data.map((review) =>
              idSet.has(review.review_id)
                ? {
                    ...review,
                    assigned_to: assigneeId,
                    assigned_to_name: assigneeName || review.assigned_to_name,
                  }
                : review
            ),
          });
        }
      }
      return { previous: queueQueries };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        for (const [queryKey, previous] of context.previous) {
          if (previous) {
            queryClient.setQueryData(queryKey, previous);
          }
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews", "queue"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "metrics"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "my-work"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "detail"] });
      setSelectedIds(new Set());
      setBulkAction("");
      setAssigningRowIds(new Set());
    },
  });

  const bulkEscalateMut = useMutation({
    mutationFn: (ids: string[]) =>
      reviewService.bulkEscalate({ review_ids: ids, reason: "Bulk escalation" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      setSelectedIds(new Set());
    },
  });

  const bulkApproveMut = useMutation({
    mutationFn: (ids: string[]) =>
      reviewService.bulkApprove({ review_ids: ids, decision: "approved" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      setSelectedIds(new Set());
    },
  });

  const [exportError, setExportError] = useState<string | null>(null);
  const exportMut = useMutation({
    mutationFn: (ids: string[]) => reviewService.bulkExport(ids),
    onMutate: () => setExportError(null),
    onError: (err) => {
      setExportError(err instanceof Error ? err.message : "Export failed");
    },
    onSettled: () => {
      // Auto-clear the error after a few seconds so it doesn't linger.
      setTimeout(() => setExportError(null), 4000);
    },
  });

  const handleExport = () => {
    // Export either the selected rows or, if nothing is selected, every
    // currently visible (filtered) row. This matches the "Export all
    // visible" pattern of ServiceNow / Salesforce list views.
    const ids =
      selectedIds.size > 0
        ? Array.from(selectedIds)
        : filtered.map((r) => r.review_id);
    if (ids.length === 0) {
      setExportError("No reviews to export");
      setTimeout(() => setExportError(null), 4000);
      return;
    }
    exportMut.mutate(ids);
  };

  // ── Queue tab counts ──

  const TERMINAL = useMemo(() => ["approved", "closed", "finalized", "archived", "rejected", "executed"], []);

  const tabCounts = useMemo(() => {
    const allActive = reviews.filter((r) => !TERMINAL.includes(r.status)).length;
    const identifiers = [user?.sub, user?.email, user?.name].filter(Boolean).map((s) => (s as string).toLowerCase());
    const myReviews = identifiers.length > 0
      ? reviews.filter((r) => {
          if (TERMINAL.includes(r.status)) return false;
          const a = (r.assigned_to || "").toLowerCase();
          const an = (r.assigned_to_name || "").toLowerCase();
          if ((!a || a === "unassigned") && !an) return false;
          return identifiers.some((id) => a === id || a.includes(id) || an === id || an.includes(id));
        }).length
      : reviews.filter((r) => r.assigned_to && r.assigned_to !== "Unassigned" && !TERMINAL.includes(r.status)).length;
    const legal = reviews.filter(
      (r) =>
        r.workflow_stage === "legal_ops" ||
        r.workflow_stage === "legal_approval" ||
        r.status === "legal_review" ||
        r.status === "legal_approval",
    ).length;
    const executive = reviews.filter(
      (r) => r.workflow_stage === "executive" || r.status === "exec_approval",
    ).length;
    const compliance = reviews.filter(
      (r) =>
        r.workflow_stage === "compliance" ||
        r.status === "compliance_review" ||
        r.status === "compliance",
    ).length;
    const escalated = reviews.filter(
      (r) => r.status === "escalated" || r.workflow_stage === "escalated",
    ).length;
    const overdue = reviews.filter(
      (r) => r.sla_status === "overdue" || r.sla_status === "critical_overdue",
    ).length;
    const completed = reviews.filter((r) => TERMINAL.includes(r.status)).length;
    const favoritesCount = reviews.filter((r) =>
      favorites.isFavorite(r.review_id) ||
      favorites.isFavorite(r.document_id || "") ||
      favorites.isFavorite(r.contract_id || ""),
    ).length;
    return { all: allActive, my: myReviews, legal, executive, compliance, escalated, overdue, completed, favorites: favoritesCount };
  }, [reviews, user, TERMINAL, favorites]);

  // ── Filtering & Sorting ──

  const filtered = useMemo(() => {
    let list = [...reviews];

    // Queue filter (role-based)
    // Terminal states excluded from default views

    if (queueFilter === "all") {
      // All active reviews — exclude terminal states
      list = list.filter((r) => !TERMINAL.includes(r.status));
    } else if (queueFilter === "my") {
      // Match by user identifier (sub / email) — the backend stores the
      // assignee as a user id (e.g. "dev-user"), not an email address, so we
      // also compare against the user.sub to support dev mode where the JWT
      // sub is the same string used by the seeder. Additionally match against
      // assigned_to_name so users assigned by display name ("Dev Admin") appear.
      const identifiers = [
        user?.sub,
        user?.email,
        user?.name,
      ]
        .filter(Boolean)
        .map((s) => (s as string).toLowerCase());
      if (identifiers.length > 0) {
        list = list.filter((r) => {
          if (TERMINAL.includes(r.status)) return false;
          const a = (r.assigned_to || "").toLowerCase();
          const an = (r.assigned_to_name || "").toLowerCase();
          if ((!a || a === "unassigned") && !an) return false;
          return identifiers.some((id) => a === id || a.includes(id) || an === id || an.includes(id));
        });
      } else {
        list = list.filter((r) => r.assigned_to && r.assigned_to !== "Unassigned" && !TERMINAL.includes(r.status));
      }
    } else if (queueFilter === "completed") {
      list = list.filter((r) => TERMINAL.includes(r.status));
    } else if (queueFilter === "legal") {
      // Match by workflow_stage "legal_ops" (set by both LEGAL_REVIEW and
      // LEGAL_APPROVAL statuses per derive_workflow_stage) OR by any
      // legal-related status value the backend may surface.
      list = list.filter(
        (r) =>
          r.workflow_stage === "legal_ops" ||
          r.workflow_stage === "legal_approval" ||
          r.status === "legal_review" ||
          r.status === "legal_approval",
      );
    } else if (queueFilter === "executive") {
      // Match by workflow_stage "executive" (set by EXEC_APPROVAL) OR by the
      // exec_approval status the backend may surface.
      list = list.filter(
        (r) => r.workflow_stage === "executive" || r.status === "exec_approval",
      );
    } else if (queueFilter === "compliance") {
      // Match by workflow_stage "compliance" OR by any compliance-related
      // status the backend may surface.
      list = list.filter(
        (r) =>
          r.workflow_stage === "compliance" ||
          r.status === "compliance_review" ||
          r.status === "compliance",
      );
    } else if (queueFilter === "escalated") {
      // Match by status "escalated" OR by workflow_stage "escalated".
      list = list.filter(
        (r) => r.status === "escalated" || r.workflow_stage === "escalated",
      );
    } else if (queueFilter === "overdue") {
      list = list.filter((r) => r.sla_status === "overdue" || r.sla_status === "critical_overdue");
    } else if (queueFilter === "favorites") {
      // Show only the user's favorited reviews (or contract ids, since the
      // review and contract are 1:1 in this app).
      list = list.filter((r) =>
        favorites.isFavorite(r.review_id) ||
        favorites.isFavorite(r.document_id || "") ||
        favorites.isFavorite(r.contract_id || ""),
      );
    }

    // Stage filter (set by queue tabs)
    if (stageFilter) {
      list = list.filter((r) => r.workflow_stage === stageFilter);
    }

    if (statusFilter !== "all") {
      list = list.filter((r) => r.status === statusFilter);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (r) =>
          (r.document_name || "").toLowerCase().includes(q) ||
          (r.original_filename || "").toLowerCase().includes(q) ||
          (r.assigned_to || "").toLowerCase().includes(q) ||
          r.review_id.toLowerCase().includes(q),
      );
    }
    list.sort((a, b) => {
      let cmp = 0;
      if (sortField === "risk_score") cmp = (a.risk_score ?? 0) - (b.risk_score ?? 0);
      else if (sortField === "priority") {
        // Priority order: critical > high > medium > low
        const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
        cmp = (order[a.priority] ?? 9) - (order[b.priority] ?? 9);
      }
      else if (sortField === "created_at") cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      else if (sortField === "updated_at") cmp = new Date(a.updated_at || a.created_at).getTime() - new Date(b.updated_at || b.created_at).getTime();
      else if (sortField === "status") cmp = a.status.localeCompare(b.status);
      else if (sortField === "assigned_to") {
        // Sort by display name, with unassigned always at the bottom
        const aName = (a.assigned_to_name || a.assigned_to || "").toLowerCase();
        const bName = (b.assigned_to_name || b.assigned_to || "").toLowerCase();
        if (!aName && bName) return sortDir === "asc" ? 1 : -1;
        if (aName && !bName) return sortDir === "asc" ? -1 : 1;
        cmp = aName.localeCompare(bName);
      }
      else if (sortField === "sla") {
        // Sort by SLA deadline; unassigned-deadline (null) at the bottom
        const aTs = a.sla_due_at || a.sla_deadline
          ? new Date(a.sla_due_at || a.sla_deadline!).getTime()
          : Number.POSITIVE_INFINITY;
        const bTs = b.sla_due_at || b.sla_deadline
          ? new Date(b.sla_due_at || b.sla_deadline!).getTime()
          : Number.POSITIVE_INFINITY;
        cmp = aTs - bTs;
      }
      return sortDir === "desc" ? -cmp : cmp;
    });
    if (maxItems) list = list.slice(0, maxItems);
    return list;
  }, [reviews, queueFilter, stageFilter, statusFilter, searchQuery, sortField, sortDir, maxItems, user, favorites]);

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortField(field); setSortDir("desc"); }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filtered.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(filtered.map((r) => r.review_id)));
  };

  const statuses = useMemo(() => {
    const set = new Set(reviews.map((r) => r.status));
    return ["all", ...Array.from(set)];
  }, [reviews]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 flex justify-center">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* ── Unified Header with Metrics Strip ── */}
      <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-bold text-navy-900 dark:text-white">Review Queue</h1>
            <span className="text-[10px] text-gray-400">
              {filtered.length === reviews.length
                ? `(${reviews.length} total)`
                : `(${filtered.length} of ${reviews.length} shown)`}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => {
                if (selectedIds.size > 0) {
                  const firstId = Array.from(selectedIds)[0];
                  const review = reviews.find((r) => r.review_id === firstId);
                  if (review) setAssignTarget(review.review_id);
                }
              }}
              disabled={selectedIds.size === 0}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              <UserPlus className="w-3 h-3" />
              Assign
            </button>
            <button
              onClick={() => {
                if (selectedIds.size > 0) {
                  bulkApproveMut.mutate(Array.from(selectedIds));
                }
              }}
              disabled={selectedIds.size === 0}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              <CheckSquare className="w-3 h-3" />
              Bulk
            </button>
            <button
              onClick={handleExport}
              disabled={exportMut.isPending}
              title={
                selectedIds.size > 0
                  ? `Export ${selectedIds.size} selected review${selectedIds.size === 1 ? "" : "s"}`
                  : `Export ${filtered.length} visible review${filtered.length === 1 ? "" : "s"}`
              }
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exportMut.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Download className="w-3 h-3" />
              )}
              Export
            </button>
          </div>
        </div>
        {/* Export error toast — appears below the toolbar for 4s after failure */}
        {exportError && (
          <div className="px-4 py-1.5 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 text-[11px] text-red-700 dark:text-red-300 flex items-center gap-2">
            <AlertTriangle className="w-3 h-3" />
            <span>{exportError}</span>
          </div>
        )}
        {metrics && (
          <>
            {/* Stage Breakdown */}
            <div className="grid grid-cols-8 border-t border-gray-100 dark:border-navy-700">
              {[
                { label: "Total", value: metrics.total, color: "text-gray-900 dark:text-white" },
                { label: "AI Analyzed", value: metrics.ai_analyzed, color: "text-blue-600" },
                { label: "Ready", value: metrics.ready_for_review, color: "text-amber-600" },
                { label: "Assigned", value: metrics.assigned, color: "text-purple-600" },
                { label: "In Review", value: metrics.in_review, color: "text-indigo-600" },
                { label: "Legal", value: metrics.legal_review, color: "text-sky-600" },
                { label: "Approved", value: metrics.approved, color: "text-green-600" },
                { label: "Closed", value: metrics.closed, color: "text-gray-600" },
              ].map((item) => (
                <div key={item.label} className="px-2 py-1.5 text-center border-r border-gray-100 dark:border-navy-700 last:border-0">
                  <p className={`text-sm font-bold ${item.color}`}>{item.value}</p>
                  <p className="text-[7px] text-gray-500 dark:text-gray-400 uppercase tracking-wider">{item.label}</p>
                </div>
              ))}
            </div>
            {/* Risk Distribution & Queue Aging — Enterprise KPI strip */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 px-3 py-3 border-t border-gray-100 dark:border-navy-700 bg-gradient-to-r from-gray-50/80 to-white dark:from-navy-900/30 dark:to-navy-800/30">
              {/* ── Risk Distribution ────────────────────────────────── */}
              <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                    <h3 className="text-[10px] font-bold text-navy-900 dark:text-white uppercase tracking-wider">
                      Risk Distribution
                    </h3>
                  </div>
                  <span className="text-[9px] font-medium text-gray-500 dark:text-gray-400">
                    {(metrics.critical_risk || 0) + (metrics.high_risk || 0)} of {metrics.total} need attention
                  </span>
                </div>
                {(() => {
                  const riskSegments = [
                    {
                      key: "critical",
                      label: "Critical",
                      value: metrics.critical_risk || 0,
                      barColor: "bg-red-500",
                      trackColor: "bg-red-100 dark:bg-red-900/30",
                      textColor: "text-red-700 dark:text-red-400",
                      dotColor: "bg-red-500",
                    },
                    {
                      key: "high",
                      label: "High",
                      value: metrics.high_risk || 0,
                      barColor: "bg-orange-500",
                      trackColor: "bg-orange-100 dark:bg-orange-900/30",
                      textColor: "text-orange-700 dark:text-orange-400",
                      dotColor: "bg-orange-500",
                    },
                    {
                      key: "medium",
                      label: "Medium",
                      value: metrics.medium_risk || 0,
                      barColor: "bg-amber-500",
                      trackColor: "bg-amber-100 dark:bg-amber-900/30",
                      textColor: "text-amber-700 dark:text-amber-400",
                      dotColor: "bg-amber-500",
                    },
                    {
                      key: "low",
                      label: "Low",
                      value: metrics.low_risk || 0,
                      barColor: "bg-emerald-500",
                      trackColor: "bg-emerald-100 dark:bg-emerald-900/30",
                      textColor: "text-emerald-700 dark:text-emerald-400",
                      dotColor: "bg-emerald-500",
                    },
                  ];
                  const total = metrics.total > 0 ? metrics.total : 1;
                  return (
                    <>
                      {/* Stacked horizontal bar */}
                      <div className="flex h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700 mb-2.5" role="img" aria-label="Risk distribution stacked bar">
                        {riskSegments.map((seg) => {
                          const pct = (seg.value / total) * 100;
                          if (pct <= 0) return null;
                          return (
                            <div
                              key={seg.key}
                              className={`${seg.barColor} transition-all`}
                              style={{ width: `${pct}%` }}
                              title={`${seg.label}: ${seg.value} (${Math.round(pct)}%)`}
                            />
                          );
                        })}
                      </div>
                      {/* Legend grid */}
                      <div className="grid grid-cols-4 gap-2">
                        {riskSegments.map((seg) => {
                          const pct = Math.round((seg.value / total) * 100);
                          return (
                            <div key={seg.key} className="flex flex-col">
                              <div className="flex items-center gap-1">
                                <span className={`w-1.5 h-1.5 rounded-full ${seg.dotColor}`} />
                                <span className={`text-[9px] font-semibold uppercase tracking-wider ${seg.textColor}`}>
                                  {seg.label}
                                </span>
                              </div>
                              <div className="flex items-baseline gap-1 mt-0.5">
                                <span className="text-base font-bold text-navy-900 dark:text-white leading-none">
                                  {seg.value}
                                </span>
                                <span className="text-[9px] text-gray-500 dark:text-gray-400">
                                  {pct}%
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  );
                })()}
              </div>

              {/* ── Queue Aging ──────────────────────────────────────── */}
              <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-amber-500" />
                    <h3 className="text-[10px] font-bold text-navy-900 dark:text-white uppercase tracking-wider">
                      Queue Aging
                    </h3>
                  </div>
                  <span className="text-[9px] font-medium text-gray-500 dark:text-gray-400">
                    {metrics.age_10_plus_days || 0} aged 10d+
                  </span>
                </div>
                {(() => {
                  const ageSegments = [
                    {
                      key: "fresh",
                      label: "0-2d",
                      sublabel: "Fresh",
                      value: metrics.age_0_2_days || 0,
                      barColor: "bg-emerald-500",
                      textColor: "text-emerald-700 dark:text-emerald-400",
                    },
                    {
                      key: "warm",
                      label: "3-5d",
                      sublabel: "On track",
                      value: metrics.age_3_5_days || 0,
                      barColor: "bg-amber-500",
                      textColor: "text-amber-700 dark:text-amber-400",
                    },
                    {
                      key: "aging",
                      label: "6-10d",
                      sublabel: "Aging",
                      value: metrics.age_6_10_days || 0,
                      barColor: "bg-orange-500",
                      textColor: "text-orange-700 dark:text-orange-400",
                    },
                    {
                      key: "stale",
                      label: "10d+",
                      sublabel: "Stale",
                      value: metrics.age_10_plus_days || 0,
                      barColor: "bg-red-500",
                      textColor: "text-red-700 dark:text-red-400",
                    },
                  ];
                  const total = metrics.total > 0 ? metrics.total : 1;
                  const maxValue = Math.max(...ageSegments.map((s) => s.value), 1);
                  return (
                    <>
                      {/* Stacked horizontal bar */}
                      <div className="flex h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700 mb-2.5" role="img" aria-label="Queue aging stacked bar">
                        {ageSegments.map((seg) => {
                          const pct = (seg.value / total) * 100;
                          if (pct <= 0) return null;
                          return (
                            <div
                              key={seg.key}
                              className={`${seg.barColor} transition-all`}
                              style={{ width: `${pct}%` }}
                              title={`${seg.label}: ${seg.value} (${Math.round(pct)}%)`}
                            />
                          );
                        })}
                      </div>
                      {/* Legend grid with proportional bars */}
                      <div className="grid grid-cols-4 gap-2">
                        {ageSegments.map((seg) => {
                          const pct = Math.round((seg.value / total) * 100);
                          const fillPct = (seg.value / maxValue) * 100;
                          return (
                            <div key={seg.key} className="flex flex-col">
                              <div className="flex items-center justify-between">
                                <span className={`text-[9px] font-semibold uppercase tracking-wider ${seg.textColor}`}>
                                  {seg.label}
                                </span>
                                <span className="text-[8px] text-gray-400 dark:text-gray-500">
                                  {seg.sublabel}
                                </span>
                              </div>
                              <div className="flex items-baseline gap-1 mt-0.5">
                                <span className="text-base font-bold text-navy-900 dark:text-white leading-none">
                                  {seg.value}
                                </span>
                                <span className="text-[9px] text-gray-500 dark:text-gray-400">
                                  {pct}%
                                </span>
                              </div>
                              {/* Per-segment mini bar */}
                              <div className="mt-1 h-0.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700">
                                <div
                                  className={`h-full ${seg.barColor} opacity-70`}
                                  style={{ width: `${Math.max(fillPct, 2)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Search & Filter Bar ── */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search contracts..."
              className="w-44 pl-7 pr-2 py-1.5 text-[11px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded-md text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-[10px] px-2 py-1.5 rounded-md border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400"
          >
            {statuses.map((s) => (
              <option key={s} value={s}>{s === "all" ? "All Status" : s.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Queue Filter Tabs ── */}
      <div className="flex items-center gap-0.5 px-4 py-1.5 bg-gray-50 dark:bg-navy-850 border-b border-gray-200 dark:border-navy-700 overflow-x-auto">
        {[
          { id: "all", label: "All Reviews", count: tabCounts.all },
          { id: "my", label: "My Reviews", count: tabCounts.my },
          { id: "legal", label: "Legal Queue", count: tabCounts.legal },
          { id: "executive", label: "Executive Queue", count: tabCounts.executive },
          { id: "compliance", label: "Compliance", count: tabCounts.compliance },
          { id: "escalated", label: "Escalated", count: tabCounts.escalated },
          { id: "overdue", label: "Overdue", count: tabCounts.overdue },
          { id: "completed", label: "Completed", count: tabCounts.completed },
          { id: "favorites", label: "Favorites", icon: Star, count: tabCounts.favorites },
        ].map((q) => (
          <button
            key={q.id}
            onClick={() => {
              setQueueFilter(q.id);
              setStageFilter("");
            }}
            className={`px-3 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-colors inline-flex items-center gap-1 ${
              queueFilter === q.id
                ? "bg-navy-900 text-white dark:bg-navy-600 dark:text-white shadow-sm"
                : "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-navy-700"
            }`}
          >
            {q.icon && <q.icon className={`w-3 h-3 ${queueFilter === q.id ? "fill-current" : ""}`} />}
            {q.label}
            {q.count !== undefined && q.count > 0 && (
              <span className="text-[9px] font-bold tabular-nums opacity-80">({q.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Bulk Action Bar ── */}
      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between px-4 py-2 bg-blue-50 dark:bg-blue-900/10 border-b border-blue-200 dark:border-blue-800">
          <span className="text-xs font-medium text-blue-700 dark:text-blue-300">
            {selectedIds.size} selected
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setBulkAction("assign")}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:hover:bg-blue-900/30 transition-colors"
            >
              <UserPlus className="w-3 h-3" /> Assign
            </button>
            <button
              onClick={() => bulkEscalateMut.mutate(Array.from(selectedIds))}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-orange-100 text-orange-700 hover:bg-orange-200 dark:bg-orange-900/20 dark:text-orange-300 transition-colors"
            >
              <ArrowUpRight className="w-3 h-3" /> Escalate
            </button>
            <button
              onClick={() => bulkApproveMut.mutate(Array.from(selectedIds))}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/20 dark:text-green-300 transition-colors"
            >
              <Check className="w-3 h-3" /> Approve
            </button>
            <button
              onClick={() => reviewService.bulkExport(Array.from(selectedIds))}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-indigo-100 text-indigo-700 hover:bg-indigo-200 dark:bg-indigo-900/20 dark:text-indigo-300 transition-colors"
            >
              <Download className="w-3 h-3" /> Export
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-navy-700 dark:text-gray-300 transition-colors"
            >
              <X className="w-3 h-3" /> Clear
            </button>
          </div>
        </div>
      )}

      {/* ── Bulk Assign Sub-Modal ── */}
      <AnimatePresence mode="wait">
        {bulkAction === "assign" && (
          <AssignModal
            key="bulk-assign"
            reviewId="bulk"
            onClose={() => setBulkAction("")}
            onAssign={(assigneeId, assigneeName) =>
              bulkAssignMut.mutate({ ids: Array.from(selectedIds), assigneeId, assigneeName })
            }
          />
        )}
      </AnimatePresence>

      {/* ── Assign Modal (single) ── */}
      <AnimatePresence mode="wait">
        {assignTarget && (
          <AssignModal
            key={`assign-${assignTarget}`}
            reviewId={assignTarget}
            onClose={() => setAssignTarget(null)}
            onAssign={(assigneeId, assigneeName) =>
              assignMut.mutate({ reviewId: assignTarget, assigneeId, assigneeName })
            }
          />
        )}
      </AnimatePresence>

      {/* ── Table (full-width, sticky header) ── */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center py-16 text-center flex-1">
          <FileText className="w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">No reviews match the current filter</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            {reviews.length === 0
              ? "Complete an upload to generate a review."
              : `${reviews.length} review${reviews.length === 1 ? "" : "s"} exist but are hidden by the active filters.`}
          </p>
          {reviews.length > 0 && (queueFilter !== "all" || stageFilter || statusFilter || searchQuery) && (
            <button
              onClick={() => {
                setQueueFilter("all");
                setStageFilter("");
                setStatusFilter("all");
                setSearchQuery("");
              }}
              className="mt-3 inline-flex items-center gap-1 px-3 py-1.5 text-[11px] font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700 transition-colors"
            >
              <X className="w-3 h-3" /> Clear filters
            </button>
          )}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-xs table-fixed">
            <thead className="sticky top-0 z-10">
              <tr className="border-b border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-850">
                <th className="w-10 px-3 py-3">
                  <button onClick={toggleSelectAll} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                    {selectedIds.size === filtered.length && filtered.length > 0
                      ? <CheckSquare className="w-3.5 h-3.5 text-blue-600" />
                      : <Square className="w-3.5 h-3.5" />
                    }
                  </button>
                </th>
                <th className="text-left px-3 py-3 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[28%]">
                  <span title="Contract name and C-Number">Contract / C-Number</span>
                </th>
                <th className="text-left px-2 py-3 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-navy-700 dark:hover:text-gray-200 w-[7%]" onClick={() => toggleSort("risk_score")}>
                  <span className="inline-flex items-center gap-1">
                    Risk <ArrowUpDown className="w-3 h-3" />
                    {sortField === "risk_score" && (
                      <span className="text-navy-600 dark:text-navy-300">{sortDir === "asc" ? "▲" : "▼"}</span>
                    )}
                  </span>
                </th>
                <th className="text-left px-2 py-3 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-navy-700 dark:hover:text-gray-200 w-[9%]" onClick={() => toggleSort("status")}>
                  <span className="inline-flex items-center gap-1">
                    Status <ArrowUpDown className="w-3 h-3" />
                    {sortField === "status" && (
                      <span className="text-navy-600 dark:text-navy-300">{sortDir === "asc" ? "▲" : "▼"}</span>
                    )}
                  </span>
                </th>
                <th
                  className="text-left px-2 py-3 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-navy-700 dark:hover:text-gray-200 w-[9%]"
                  onClick={() => toggleSort("assigned_to")}
                >
                  <span className="inline-flex items-center gap-1">
                    Assigned <ArrowUpDown className="w-3 h-3" />
                    {sortField === "assigned_to" && (
                      <span className="text-navy-600 dark:text-navy-300">{sortDir === "asc" ? "▲" : "▼"}</span>
                    )}
                  </span>
                </th>
                <th
                  className="text-left px-2 py-3 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-navy-700 dark:hover:text-gray-200 w-[9%]"
                  onClick={() => toggleSort("created_at")}
                >
                  <span className="inline-flex items-center gap-1">
                    Created <ArrowUpDown className="w-3 h-3" />
                    {sortField === "created_at" && (
                      <span className="text-navy-600 dark:text-navy-300">{sortDir === "asc" ? "▲" : "▼"}</span>
                    )}
                  </span>
                </th>
                <th
                  className="text-left px-2 py-3 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-navy-700 dark:hover:text-gray-200 w-[9%]"
                  onClick={() => toggleSort("updated_at")}
                >
                  <span className="inline-flex items-center gap-1">
                    Updated <ArrowUpDown className="w-3 h-3" />
                    {sortField === "updated_at" && (
                      <span className="text-navy-600 dark:text-navy-300">{sortDir === "asc" ? "▲" : "▼"}</span>
                    )}
                  </span>
                </th>
                <th
                  className="text-left px-2 py-3 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-navy-700 dark:hover:text-gray-200 w-[7%]"
                  onClick={() => toggleSort("sla")}
                >
                  <span className="inline-flex items-center gap-1">
                    SLA <ArrowUpDown className="w-3 h-3" />
                    {sortField === "sla" && (
                      <span className="text-navy-600 dark:text-navy-300">{sortDir === "asc" ? "▲" : "▼"}</span>
                    )}
                  </span>
                </th>
                <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider w-[18%]">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
              {filtered.map((review) => {
                const sla = formatSLA(review);
                const isSelected = selectedIds.has(review.review_id);
                const contractName = formatContractTitle(review);
                const rawFilename = review.original_filename || "";
                const isOverdue = sla.status === "overdue" || sla.status === "critical_overdue";
                return (
                  <tr
                    key={review.review_id}
                    className={`hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors cursor-pointer ${
                      isSelected ? "bg-blue-50/50 dark:bg-blue-900/10" : "bg-white dark:bg-navy-800"
                    } ${isOverdue ? "border-l-2 border-l-red-400" : ""} ${
                      assigningRowId === review.review_id ||
                      assigningRowIds.has(review.review_id)
                        ? "opacity-70"
                        : ""
                    }`}
                    onClick={() => onReviewSelect?.(review.review_id)}
                  >
                    <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => toggleSelect(review.review_id)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                      >
                        {isSelected
                          ? <CheckSquare className="w-3.5 h-3.5 text-blue-600" />
                          : <Square className="w-3.5 h-3.5" />
                        }
                      </button>
                    </td>
                    {/* ── Contract Column (expanded, two-line) ── */}
                    <td className="px-3 py-2.5">
                      <div className="group relative flex items-start gap-2.5">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
                          review.priority === "critical" ? "bg-red-100 dark:bg-red-900/20" :
                          review.priority === "high" ? "bg-orange-100 dark:bg-orange-900/20" :
                          review.priority === "medium" ? "bg-amber-100 dark:bg-amber-900/20" :
                          "bg-gray-100 dark:bg-navy-700"
                        }`}>
                          <FileText className={`w-4 h-4 ${
                            review.priority === "critical" ? "text-red-600 dark:text-red-400" :
                            review.priority === "high" ? "text-orange-600 dark:text-orange-400" :
                            review.priority === "medium" ? "text-amber-600 dark:text-amber-400" :
                            "text-gray-500 dark:text-gray-400"
                          }`} />
                        </div>
                        <div className="min-w-0 flex-1">
                          {/* Primary: Contract name */}
                          <div className="flex items-center gap-2">
                            {review.contract_number && (
                              <span className="text-[10px] font-mono text-gray-400 dark:text-gray-500 flex-shrink-0">{review.contract_number}</span>
                            )}
                            <p className="text-[12px] font-semibold text-navy-900 dark:text-white truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                              {contractName}
                            </p>
                            <button
                              type="button"
                              aria-label={favorites.isFavorite(review.review_id) ? "Unfavorite review" : "Favorite review"}
                              aria-pressed={favorites.isFavorite(review.review_id)}
                              data-testid="review-favorite-toggle"
                              onClick={(e) => { e.stopPropagation(); favorites.toggle(review.review_id); }}
                              className={`flex-shrink-0 p-0.5 rounded transition-colors ${
                                favorites.isFavorite(review.review_id)
                                  ? "text-amber-500 hover:text-amber-600"
                                  : "text-gray-400 hover:text-amber-500 dark:text-gray-500"
                              }`}
                            >
                              <Star className={`w-3.5 h-3.5 ${favorites.isFavorite(review.review_id) ? "fill-current" : ""}`} />
                            </button>
                            <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0 ${
                              review.priority === "critical"
                                ? "bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-300"
                                : review.priority === "high"
                                ? "bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-300"
                                : review.priority === "medium"
                                ? "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
                                : "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300"
                            }`}>{review.priority}</span>
                          {/* Lifecycle Stage Badge */}
                          {(() => {
                            const isExpired = review.status === "executed" && (review.sla_status === "critical_overdue" || review.sla_status === "overdue");
                            const isActive = review.status === "executed" && !isExpired;
                            if (review.status === "archived" || review.status === "closed") return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-gray-400 flex-shrink-0">Closed</span>;
                            if (isExpired) return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-300 flex-shrink-0">Expired</span>;
                            if (isActive) return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300 flex-shrink-0">Active</span>;
                            if (review.status === "finalized") return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300 flex-shrink-0">Finalized</span>;
                            if (review.status === "approved") return <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300 flex-shrink-0">Approved</span>;
                            return null;
                          })()}
                          </div>
                          {/* Secondary: Metadata row — tight grouping */}
                          <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                            <span className="text-[10px] font-medium text-gray-600 dark:text-gray-400">
                              {review.document_type || "Contract"}
                            </span>
                            <span className="w-1 h-1 rounded-full bg-gray-300 dark:bg-navy-600" />
                            <span className="text-[9px] text-gray-400 dark:text-gray-500">
                              {review.finding_count} findings
                            </span>
                            {review.redline_count > 0 && (
                              <>
                                <span className="w-1 h-1 rounded-full bg-gray-300 dark:bg-navy-600" />
                                <span className="text-[9px] text-gray-400 dark:text-gray-500">
                                  {review.redline_count} redlines
                                </span>
                              </>
                            )}
                            <span className="w-1 h-1 rounded-full bg-gray-300 dark:bg-navy-600" />
                            <span className="text-[9px] text-gray-400 dark:text-gray-500">
                              {stageLabel(review.status, review.workflow_stage)}
                            </span>
                            {rawFilename && (
                              <span className="text-[8px] text-gray-300 dark:text-gray-600 truncate max-w-[100px] ml-1" title={rawFilename}>
                                {rawFilename}
                              </span>
                            )}
                          </div>
                        </div>
                        {/* ── Hover Tooltip Preview ── */}
                        <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-150 absolute z-40 w-[380px] max-w-[380px] md:max-w-[90vw] bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded-lg shadow-xl pointer-events-none"
                             style={{ top: '50%', left: 'calc(100% + 12px)', transform: 'translateY(-50%)', maxHeight: '60vh', overflowY: 'auto' }}>
                          <div className="p-3 space-y-2">
                            <div className="flex items-center gap-2">
                              <FileText className="w-4 h-4 text-navy-500 flex-shrink-0" />
                              <span className="text-base font-semibold text-navy-900 dark:text-white break-words leading-tight">
                                {review.contract_number ? `${review.contract_number} ` : ""}{contractName}
                              </span>
                            </div>
                            {rawFilename && rawFilename !== contractName && (
                              <div className="text-[10px] text-gray-400 dark:text-gray-500 font-mono truncate" title={rawFilename}>
                                {rawFilename}
                              </div>
                            )}
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              {review.status.replace(/_/g, " ")} • {review.risk_score != null ? `${(review.risk_score * 100).toFixed(0)}% Risk` : "—"} • {review.finding_count} Findings • {review.redline_count} Redlines
                            </div>
                            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                              <span>Contract: <span className="font-medium text-gray-700 dark:text-gray-200 font-mono">{review.contract_number || "—"}</span></span>
                              <span>Review: <span className="font-medium text-gray-700 dark:text-gray-200 font-mono">{review.review_number || review.review_id.slice(0, 8)}</span></span>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                              <span>Assignee: <span className="font-medium text-gray-700 dark:text-gray-200">{review.assigned_to_name || review.assigned_to || "Unassigned"}</span></span>
                              <span>Created: <span className="font-medium text-gray-700 dark:text-gray-200">{new Date(review.created_at).toLocaleDateString()}</span></span>
                            </div>
                            {rawFilename && (
                              <div className="pt-1.5 border-t border-gray-100 dark:border-navy-600">
                                <span className="text-[10px] text-gray-400 block mb-0.5">File</span>
                                <span className="text-xs text-gray-700 dark:text-gray-300 break-all break-words whitespace-normal leading-relaxed max-h-12 overflow-hidden block hover:overflow-visible hover:max-h-none" title={rawFilename}>{rawFilename}</span>
                              </div>
                            )}
                            {isOverdue && (
                              <div className="flex items-center gap-1 text-[10px] text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/10 rounded px-2 py-1">
                                <AlertTriangle className="w-3 h-3" /> SLA Overdue by {Math.round(review.overdue_hours)}h
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>
                    {/* ── Risk ── */}
                    <td className="px-2 py-3 align-top pt-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium ${riskColor(review.risk_score)}`}>
                        {review.risk_score != null ? `${(review.risk_score * 100).toFixed(0)}%` : "—"}
                      </span>
                    </td>
                    {/* ── Status ── */}
                    <td className="px-2 py-3 align-top pt-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium ${statusColor(review.status)}`}>
                        {review.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    {/* ── Assigned ── */}
                    <td className="px-2 py-3 align-top pt-3.5">
                      {(() => {
                        const displayName = review.assigned_to_name || review.assigned_to;
                        const hasAssignee = Boolean(displayName);
                        const isRowAssigning =
                          assigningRowId === review.review_id ||
                          assigningRowIds.has(review.review_id);
                        return (
                          <div className="flex items-center gap-1.5">
                            <div
                              data-testid={`assigned-avatar-${review.review_id}`}
                              className={`w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold flex-shrink-0 ${
                                hasAssignee
                                  ? "bg-navy-100 text-navy-600 dark:bg-navy-700 dark:text-navy-300"
                                  : "bg-gray-100 text-gray-400 dark:bg-navy-700 dark:text-gray-500"
                              }`}
                            >
                              {isRowAssigning ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : hasAssignee ? (
                                displayName
                                  .split(/\s+/)
                                  .map((n) => n[0] || "")
                                  .join("")
                                  .slice(0, 2)
                                  .toUpperCase()
                              ) : (
                                "—"
                              )}
                            </div>
                            <span
                              data-testid={`assigned-name-${review.review_id}`}
                              className={`text-[10px] truncate max-w-[90px] ${
                                hasAssignee
                                  ? "text-gray-700 dark:text-gray-300 font-medium"
                                  : "italic text-gray-400 dark:text-gray-500"
                              }`}
                              title={displayName || "Unassigned"}
                            >
                              {isRowAssigning ? "Assigning…" : displayName || "Unassigned"}
                            </span>
                            {hasAssignee && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setAssignTarget(review.review_id);
                                }}
                                className="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-navy-700 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors flex-shrink-0"
                                title="Reassign"
                              >
                                <RefreshCw className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        );
                      })()}
                    </td>
                    {/* ── Created Date ── */}
                    <td className="px-2 py-3 align-top pt-3.5">
                      <span className="text-[10px] text-gray-600 dark:text-gray-400 whitespace-nowrap">
                        {review.created_at ? new Date(review.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                      </span>
                    </td>
                    {/* ── Updated Date ── */}
                    <td className="px-2 py-3 align-top pt-3.5">
                      <span className="text-[10px] text-gray-600 dark:text-gray-400 whitespace-nowrap">
                        {review.updated_at ? new Date(review.updated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                      </span>
                    </td>
                    {/* ── SLA / Due Date ── */}
                    <td className="px-2 py-3 align-top pt-3.5">
                      <div className="flex flex-col gap-0.5">
                        <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium ${slaColor(sla.status)}`}>
                          {sla.status === "overdue" && <AlertTriangle className="w-3 h-3" />}
                          {sla.status === "warning" && <Clock className="w-3 h-3" />}
                          {sla.label}
                        </span>
                        {review.sla_deadline && (
                          <span className="text-[8px] text-gray-400 dark:text-gray-500 whitespace-nowrap">
                            Due: {new Date(review.sla_deadline).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                          </span>
                        )}
                      </div>
                    </td>
                    {/* ── Actions ── */}
                    <td className="px-3 py-3 text-right align-top pt-3">
                      <div className="flex items-center justify-end gap-1">
                        {(() => {
                          const rowActions = getAllowedActions(review.status);
                          const rowImmutable = isImmutable(review.status);
                          if (rowImmutable) {
                            return (
                              <span className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium text-gray-400 dark:text-gray-500">
                                <Lock className="w-3 h-3" />
                                {getStatusLabel(review.status)}
                              </span>
                            );
                          }
                          return (
                            <>
                              {!review.assigned_to && rowActions.canAssign && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setAssignTarget(review.review_id); }}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:hover:bg-amber-900/30 transition-colors"
                                  title="Assign reviewer"
                                >
                                  <UserPlus className="w-3 h-3" />
                                </button>
                              )}
                              {rowActions.canApprove && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setApprovalTarget(review); }}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/20 dark:text-green-300 dark:hover:bg-green-900/30 transition-colors"
                                  title="Approve review"
                                >
                                  <ThumbsUp className="w-3 h-3" />
                                </button>
                              )}
                              {rowActions.canEscalate && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setEscalationTarget(review); }}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-orange-100 text-orange-700 hover:bg-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:hover:bg-orange-900/30 transition-colors"
                                  title="Escalate review"
                                >
                                  <ArrowUpRight className="w-3 h-3" />
                                </button>
                              )}
                              {/* Finalize — for approved contracts */}
                              {rowActions.canFinalize && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); finalizeMut.mutate(review.review_id); }}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:hover:bg-blue-900/30 transition-colors"
                                  title="Finalize contract"
                                >
                                  <CheckCircle2 className="w-3 h-3" />
                                </button>
                              )}
                              {/* Close — for finalized or executed contracts */}
                              {(review.status === "finalized" || review.status === "executed") && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleCloseReview(review.review_id, review.contract_number || review.document_name || "Contract"); }}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
                                  title="Close contract"
                                >
                                  <Archive className="w-3 h-3" />
                                </button>
                              )}
                              <button
                                onClick={(e) => { e.stopPropagation(); onReviewSelect?.(review.review_id); }}
                                className="inline-flex items-center gap-1 px-2.5 py-1 text-[9px] font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700 dark:bg-navy-500 dark:hover:bg-navy-600 transition-colors shadow-sm"
                                title="Open review workspace"
                              >
                                <Eye className="w-3 h-3" /> Open
                              </button>
                            </>
                          );
                        })()}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Footer ── */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-850 text-[10px] text-gray-500 dark:text-gray-400 flex-shrink-0">
        <span>{filtered.length} of {reviews.length} reviews</span>
        <span className="flex items-center gap-3">
          {metrics && (
            <>
              <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-400" /> {metrics.total - metrics.sla_at_risk - metrics.overdue} on track
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-400" /> {metrics.sla_at_risk || 0} at risk
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-400" /> {metrics.overdue || 0} overdue
              </span>
            </>
          )}
        </span>
      </div>

      {/* ── Approval Modal ── */}
      <AnimatePresence mode="wait">
        {approvalTarget && (
          <ApprovalModal
            key={`approve-${approvalTarget.review_id}`}
            reviewId={approvalTarget.review_id}
            reviewTitle={approvalTarget.document_name || approvalTarget.original_filename || `Review ${approvalTarget.review_id.slice(0, 8)}`}
            riskScore={approvalTarget.risk_score ?? undefined}
            openObligations={openObligationCounts[approvalTarget.review_id] ?? 0}
            onApprove={async (decision, comment, conditions) => {
              await approveMut.mutateAsync({ reviewId: approvalTarget.review_id, decision, comment, conditions });
            }}
            onReject={async (comment, category, severity) => {
              await rejectMut.mutateAsync({ reviewId: approvalTarget.review_id, comment, category, severity });
            }}
            onClose={() => setApprovalTarget(null)}
            isLoading={approveMut.isPending || rejectMut.isPending}
          />
        )}
      </AnimatePresence>

      {/* ── Escalation Modal ── */}
      <AnimatePresence mode="wait">
        {escalationTarget && (
          <EscalationModal
            key={`escalate-${escalationTarget.review_id}`}
            reviewId={escalationTarget.review_id}
            reviewTitle={escalationTarget.document_name || escalationTarget.original_filename || `Review ${escalationTarget.review_id.slice(0, 8)}`}
            currentPriority={escalationTarget.priority}
            currentStage={escalationTarget.workflow_stage}
            onEscalate={async (reason, escalatedTo, raisePriority, targetStage) => {
              await escalateMut.mutateAsync({
                reviewId: escalationTarget.review_id,
                reason,
                escalatedTo,
                raisePriority,
                targetStage,
              });
            }}
            onClose={() => setEscalationTarget(null)}
            isLoading={escalateMut.isPending}
          />
        )}
      </AnimatePresence>

      {/* ── Close Confirmation Modal ── */}
      <AnimatePresence mode="wait">
        {closeTarget && (
          <motion.div key={`close-${closeTarget.id}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => { setCloseTarget(null); setCloseReason(""); }}>
            <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
              className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-sm mx-4 p-5" onClick={e => e.stopPropagation()}>
              <h3 className="text-sm font-semibold text-navy-900">Close Contract</h3>
              <p className="text-[11px] text-gray-500 mt-1">Close "{closeTarget.name}"? This will archive the contract.</p>
              <p className="text-[10px] text-amber-600 mt-1">Open obligations will block this action.</p>
              <div className="mt-3">
                <label className="text-[10px] font-semibold text-gray-600">Reason for closing <span className="text-red-500">*</span></label>
                <textarea value={closeReason} onChange={e => setCloseReason(e.target.value)}
                  placeholder="Enter the reason for closing this contract..."
                  rows={2}
                  className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400 resize-none"
                  autoFocus
                />
                {closeReason.trim().length > 0 && closeReason.trim().length < 5 && (
                  <p className="text-[9px] text-red-500 mt-0.5">Please enter at least 5 characters</p>
                )}
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button onClick={() => { setCloseTarget(null); setCloseReason(""); }}
                  className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
                <button onClick={() => closeMut.mutate({ reviewId: closeTarget.id, reason: closeReason.trim() })}
                  disabled={closeMut.isPending || closeReason.trim().length < 5}
                  className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-gray-700 text-white hover:bg-gray-800 disabled:opacity-50">
                  {closeMut.isPending ? "Closing..." : "Close Contract"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

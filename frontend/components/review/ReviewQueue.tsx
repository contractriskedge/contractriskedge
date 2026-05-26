/**
 * ReviewQueue — enterprise review queue with interactive operations.
 *
 * Features:
 * - Workload metrics bar (Unassigned / In Review / Overdue / Escalated / Critical)
 * - Multi-select with bulk actions (Assign / Escalate / Approve)
 * - Assign modal with reviewer picker
 * - SLA status with color-coded badges (on_track / warning / overdue)
 * - Workflow stage display
 * - Optimistic UI updates
 * - Click to open review
 * - Action buttons disabled for immutable states
 */

"use client";

import React, { useState, useMemo, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText, AlertTriangle, Clock, User, ArrowUpDown, Lock,
  Search, Check, X, Loader2, UserPlus, ArrowUpRight,
  CheckSquare, Square, ChevronDown, Eye, ThumbsUp, ThumbsDown, Download,
} from "lucide-react";
import { reviewService } from "@/services/api/reviews";
import { api } from "@/services/api/client";
import type { ReviewDetail, WorkloadMetrics } from "@/services/api/client";
import { ApprovalModal } from "./ApprovalModal";
import { EscalationModal } from "./EscalationModal";
import { getAllowedActions, isImmutable, getStatusLabel } from "@/lib/workflow";

// ── Hooks ───────────────────────────────────────────────────────

function useReviewsList() {
  return useQuery({
    queryKey: ["reviews", "queue"],
    queryFn: () => reviewService.list({ page_size: 100 }),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

function useWorkloadMetrics() {
  return useQuery({
    queryKey: ["reviews", "workload"],
    queryFn: () => reviewService.getWorkloadMetrics(),
    staleTime: 15_000,
    refetchInterval: 30_000,
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

function formatSLA(review: ReviewDetail): { label: string; status: string } {
  if (review.status === "approved" || review.status === "closed" || review.status === "rejected") {
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

function useReviewers() {
  return useQuery({
    queryKey: ["admin", "users", "reviewers"],
    queryFn: async () => {
      const users = await api.get<Array<{ user_id: string; name: string | null; role: string; is_active: boolean }>>(
        "/admin/users",
      );
      return users
        .filter((u) => u.is_active && (u.role === "reviewer" || u.role === "legal_ops"))
        .map((u) => ({ user_id: u.user_id, name: u.name || u.user_id }));
    },
    staleTime: 60_000,
  });
}

// ── Assign Modal ────────────────────────────────────────────────

function AssignModal({
  reviewId,
  onClose,
  onAssign,
}: {
  reviewId: string;
  onClose: () => void;
  onAssign: (assigneeId: string, assigneeName: string) => void;
}) {
  const { data: reviewers = [], isLoading } = useReviewers();
  const [selected, setSelected] = useState("");
  const [search, setSearch] = useState("");

  const filtered = reviewers.filter((r) =>
    r.name.toLowerCase().includes(search.toLowerCase()),
  );

  const selectedReviewer = reviewers.find((r) => r.user_id === selected);

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
        className="bg-white rounded-xl shadow-xl border border-gray-200 w-80 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-navy-900">Assign Reviewer</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-3">
          <div className="relative mb-2">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search reviewers..."
              className="w-full pl-7 pr-2 py-1.5 text-xs border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
              autoFocus
            />
          </div>
          <div className="max-h-48 overflow-y-auto space-y-0.5">
            {isLoading && (
              <p className="text-xs text-gray-400 text-center py-4">Loading reviewers...</p>
            )}
            {!isLoading && filtered.map((reviewer) => (
              <button
                key={reviewer.user_id}
                onClick={() => setSelected(reviewer.user_id)}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-colors ${
                  selected === reviewer.user_id
                    ? "bg-blue-50 text-blue-700"
                    : "hover:bg-gray-50 text-gray-700"
                }`}
              >
                <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center">
                  <User className="w-3 h-3 text-gray-500" />
                </div>
                <span>{reviewer.name}</span>
                {selected === reviewer.user_id && <Check className="w-3 h-3 ml-auto text-blue-600" />}
              </button>
            ))}
            {!isLoading && filtered.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-4">No reviewers found</p>
            )}
          </div>
        </div>
        <div className="px-3 py-2 border-t border-gray-100 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-[10px] font-medium text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => selectedReviewer && onAssign(selectedReviewer.user_id, selectedReviewer.name)}
            disabled={!selectedReviewer}
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
  const { data, isLoading } = useReviewsList();
  const { data: metrics } = useWorkloadMetrics();

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [stageFilter, setStageFilter] = useState<string>("");
  const [queueFilter, setQueueFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<"risk_score" | "created_at" | "status" | "priority">("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [assignTarget, setAssignTarget] = useState<string | null>(null);
  const [approvalTarget, setApprovalTarget] = useState<ReviewDetail | null>(null);
  const [escalationTarget, setEscalationTarget] = useState<ReviewDetail | null>(null);
  const [bulkAction, setBulkAction] = useState<string>("");

  const reviews = data?.data ?? [];

  // ── Mutations ──

  const assignMut = useMutation({
    mutationFn: ({ reviewId, assigneeId }: { reviewId: string; assigneeId: string; assigneeName: string }) =>
      reviewService.assign(reviewId, { assignee_id: assigneeId }),
    onMutate: async ({ reviewId, assigneeId, assigneeName }) => {
      await queryClient.cancelQueries({ queryKey: ["reviews", "queue"] });
      const previous = queryClient.getQueryData<{ data: ReviewDetail[] }>(["reviews", "queue"]);
      if (previous) {
        queryClient.setQueryData(["reviews", "queue"], {
          ...previous,
          data: previous.data.map((review) =>
            review.review_id === reviewId
              ? { ...review, assigned_to: assigneeName, status: "in_review", workflow_stage: "reviewer" }
              : review,
          ),
        });
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["reviews", "queue"], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews", "queue"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      setAssignTarget(null);
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

  // ── Escalate Mutation ──

  const escalateMut = useMutation({
    mutationFn: ({ reviewId, reason, escalatedTo, raisePriority, targetStage }: {
      reviewId: string; reason: string; escalatedTo?: string; raisePriority?: boolean; targetStage?: string;
    }) =>
      reviewService.escalate(reviewId, { reason, escalated_to: escalatedTo, raise_priority: raisePriority, target_workflow_stage: targetStage }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      setEscalationTarget(null);
    },
  });

  const bulkAssignMut = useMutation({
    mutationFn: ({ ids, assigneeId }: { ids: string[]; assigneeId: string; assigneeName: string }) =>
      reviewService.bulkAssign({ review_ids: ids, assignee_id: assigneeId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", "workload"] });
      setSelectedIds(new Set());
      setBulkAction("");
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

  // ── Filtering & Sorting ──

  const filtered = useMemo(() => {
    let list = [...reviews];

    // Queue filter (role-based)
    if (queueFilter === "my") {
      list = list.filter((r) => r.assigned_to && r.assigned_to !== "Unassigned");
    } else if (queueFilter === "legal") {
      list = list.filter((r) => r.status === "legal_approval" || r.workflow_stage === "legal_approval");
    } else if (queueFilter === "executive") {
      list = list.filter((r) => r.status === "exec_approval" || r.workflow_stage === "executive");
    } else if (queueFilter === "compliance") {
      list = list.filter((r) => r.workflow_stage === "compliance");
    } else if (queueFilter === "escalated") {
      list = list.filter((r) => r.status === "escalated" || r.status === "legal_approval" || r.status === "exec_approval");
    } else if (queueFilter === "overdue") {
      list = list.filter((r) => r.sla_status === "overdue" || r.sla_status === "critical_overdue");
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
      else if (sortField === "priority") cmp = (a.priority || "normal").localeCompare(b.priority || "normal");
      else if (sortField === "created_at") cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      else if (sortField === "status") cmp = a.status.localeCompare(b.status);
      return sortDir === "desc" ? -cmp : cmp;
    });
    if (maxItems) list = list.slice(0, maxItems);
    return list;
  }, [reviews, queueFilter, stageFilter, statusFilter, searchQuery, sortField, sortDir, maxItems]);

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
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* ── Workload Metrics Bar ── */}
      {metrics && (
        <div className="grid grid-cols-5 gap-px bg-gray-100 border-b border-gray-200">
          {[
            { label: "Unassigned", value: metrics.unassigned, color: "text-amber-600", bg: "bg-amber-50" },
            { label: "In Review", value: metrics.in_review, color: "text-purple-600", bg: "bg-purple-50" },
            { label: "Overdue", value: metrics.overdue, color: "text-red-600", bg: "bg-red-50" },
            { label: "Escalated", value: metrics.escalated, color: "text-orange-600", bg: "bg-orange-50" },
            { label: "Critical", value: metrics.critical, color: "text-rose-600", bg: "bg-rose-50" },
          ].map((item) => (
            <div key={item.label} className={`${item.bg} px-3 py-2 text-center`}>
              <p className={`text-lg font-bold ${item.color}`}>{item.value}</p>
              <p className="text-[9px] text-gray-500">{item.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Header ── */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-gray-500" />
          <h3 className="text-sm font-semibold text-navy-900">Review Queue</h3>
          <span className="text-[10px] text-gray-400">({reviews.length} total)</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search contracts..."
              className="w-36 pl-7 pr-2 py-1 text-[10px] border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
            />
          </div>
          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-[10px] border border-gray-300 rounded-lg px-2 py-1 focus:border-blue-500 focus:outline-none"
          >
            {statuses.map((s) => (
              <option key={s} value={s}>{s === "all" ? "All Status" : s.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Queue Filter Tabs ── */}
      <div className="px-4 py-2 border-b border-gray-100 bg-gray-50 flex items-center gap-1 overflow-x-auto">
        {[
          { id: "all", label: "All Reviews" },
          { id: "my", label: "My Reviews" },
          { id: "legal", label: "Legal Queue", stage: "legal_approval" },
          { id: "executive", label: "Executive Queue", stage: "executive" },
          { id: "compliance", label: "Compliance Queue", stage: "compliance" },
          { id: "escalated", label: "Escalated" },
          { id: "overdue", label: "Overdue" },
        ].map((q) => (
          <button
            key={q.id}
            onClick={() => {
              setQueueFilter(q.id);
              if (q.stage) setStageFilter(q.stage);
              else setStageFilter("");
            }}
            className={`px-2.5 py-1 text-[10px] font-medium rounded-lg whitespace-nowrap transition-colors ${
              queueFilter === q.id
                ? "bg-navy-900 text-white"
                : "text-gray-600 hover:bg-gray-200"
            }`}
          >
            {q.label}
          </button>
        ))}
      </div>

      {/* ── Bulk Action Bar ── */}
      {selectedIds.size > 0 && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 flex items-center justify-between">
          <span className="text-xs font-medium text-blue-700">
            {selectedIds.size} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setBulkAction("assign")}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-blue-100 text-blue-700 hover:bg-blue-200"
            >
              <UserPlus className="w-3 h-3" /> Assign
            </button>
            <button
              onClick={() => bulkEscalateMut.mutate(Array.from(selectedIds))}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-orange-100 text-orange-700 hover:bg-orange-200"
            >
              <ArrowUpRight className="w-3 h-3" /> Escalate
            </button>
            <button
              onClick={() => bulkApproveMut.mutate(Array.from(selectedIds))}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-green-100 text-green-700 hover:bg-green-200"
            >
              <Check className="w-3 h-3" /> Approve
            </button>
            <button
              onClick={() => reviewService.bulkExport(Array.from(selectedIds))}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200"
            >
              <Download className="w-3 h-3" /> Export
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
            >
              <X className="w-3 h-3" /> Clear
            </button>
          </div>
        </div>
      )}

      {/* ── Bulk Assign Sub-Modal ── */}
      {bulkAction === "assign" && (
        <AssignModal
          reviewId="bulk"
          onClose={() => setBulkAction("")}
          onAssign={(assigneeId, assigneeName) =>
            bulkAssignMut.mutate({ ids: Array.from(selectedIds), assigneeId, assigneeName })
          }
        />
      )}

      {/* ── Assign Modal (single) ── */}
      <AnimatePresence>
        {assignTarget && (
          <AssignModal
            reviewId={assignTarget}
            onClose={() => setAssignTarget(null)}
            onAssign={(assigneeId, assigneeName) =>
              assignMut.mutate({ reviewId: assignTarget, assigneeId, assigneeName })
            }
          />
        )}
      </AnimatePresence>

      {/* ── Table ── */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center py-12 text-center">
          <FileText className="w-10 h-10 text-gray-300 mb-3" />
          <p className="text-sm text-gray-500">No reviews found</p>
          <p className="text-xs text-gray-400 mt-1">Complete an upload to generate a review.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="w-8 px-2 py-2.5">
                  <button onClick={toggleSelectAll} className="text-gray-400 hover:text-gray-600">
                    {selectedIds.size === filtered.length && filtered.length > 0
                      ? <CheckSquare className="w-3.5 h-3.5 text-blue-600" />
                      : <Square className="w-3.5 h-3.5" />
                    }
                  </button>
                </th>
                <th className="text-left px-2 py-2.5 font-medium text-gray-500">Contract</th>
                <th className="text-left px-2 py-2.5 font-medium text-gray-500 cursor-pointer" onClick={() => toggleSort("risk_score")}>
                  <span className="inline-flex items-center gap-1">Risk <ArrowUpDown className="w-3 h-3" /></span>
                </th>
                <th className="text-left px-2 py-2.5 font-medium text-gray-500 cursor-pointer" onClick={() => toggleSort("status")}>
                  <span className="inline-flex items-center gap-1">Status <ArrowUpDown className="w-3 h-3" /></span>
                </th>
                <th className="text-left px-2 py-2.5 font-medium text-gray-500">Assigned</th>
                <th className="text-left px-2 py-2.5 font-medium text-gray-500">SLA</th>
                <th className="text-left px-2 py-2.5 font-medium text-gray-500">Stage</th>
                <th className="text-right px-3 py-2.5 font-medium text-gray-500">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((review) => {
                const sla = formatSLA(review);
                const isSelected = selectedIds.has(review.review_id);
                return (
                  <tr
                    key={review.review_id}
                    className={`hover:bg-gray-50 transition-colors cursor-pointer ${
                      isSelected ? "bg-blue-50/50" : ""
                    } ${sla.status === "overdue" ? "border-l-2 border-l-red-400" : ""}`}
                    onClick={() => onReviewSelect?.(review.review_id)}
                  >
                    <td className="px-2 py-3" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => toggleSelect(review.review_id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        {isSelected
                          ? <CheckSquare className="w-3.5 h-3.5 text-blue-600" />
                          : <Square className="w-3.5 h-3.5" />
                        }
                      </button>
                    </td>
                    <td className="px-2 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-navy-900 truncate max-w-[140px]">
                              {review.document_name || review.original_filename || `Review ${review.review_id.slice(0, 8)}`}
                            </p>
                            <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full ${
                              review.priority === "critical"
                                ? "bg-red-100 text-red-700"
                                : review.priority === "high"
                                ? "bg-orange-100 text-orange-700"
                                : review.priority === "medium"
                                ? "bg-amber-100 text-amber-700"
                                : "bg-green-100 text-green-700"
                            }`}>{review.priority}</span>
                          </div>
                          <p className="text-[9px] text-gray-400">
                            {review.finding_count} findings &middot; {review.redline_count} redlines
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-2 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium ${riskColor(review.risk_score)}`}>
                        {review.risk_score != null ? `${(review.risk_score * 100).toFixed(0)}%` : "—"}
                      </span>
                    </td>
                    <td className="px-2 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-medium ${statusColor(review.status)}`}>
                        {review.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-2 py-3">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3 h-3 text-gray-400" />
                        <span className={`text-gray-600 ${!review.assigned_to ? "italic text-gray-400" : ""}`}>
                          {review.assigned_to || "Unassigned"}
                        </span>
                      </div>
                    </td>
                    <td className="px-2 py-3">
                      <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium ${slaColor(sla.status)}`}>
                        {sla.status === "overdue" && <AlertTriangle className="w-3 h-3" />}
                        {sla.status === "warning" && <Clock className="w-3 h-3" />}
                        {sla.label}
                      </span>
                    </td>
                    <td className="px-2 py-3">
                      <span className="text-[10px] text-gray-500">
                        {stageLabel(review.status, review.workflow_stage)}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {(() => {
                          const rowActions = getAllowedActions(review.status);
                          const rowImmutable = isImmutable(review.status);
                          if (rowImmutable) {
                            return (
                              <span className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium text-gray-400">
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
                                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-lg bg-amber-100 text-amber-700 hover:bg-amber-200 transition-colors"
                                >
                                  <UserPlus className="w-3 h-3" /> Assign
                                </button>
                              )}
                              {rowActions.canApprove && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setApprovalTarget(review); }}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-lg bg-green-100 text-green-700 hover:bg-green-200 transition-colors"
                                >
                                  <ThumbsUp className="w-3 h-3" /> Approve
                                </button>
                              )}
                              {rowActions.canEscalate && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setEscalationTarget(review); }}
                                  className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-lg bg-orange-100 text-orange-700 hover:bg-orange-200 transition-colors"
                                >
                                  <ArrowUpRight className="w-3 h-3" /> Escalate
                                </button>
                              )}
                              <button
                                onClick={(e) => { e.stopPropagation(); onReviewSelect?.(review.review_id); }}
                                className="inline-flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors"
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

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-100 bg-gray-50 text-[10px] text-gray-400 flex items-center justify-between">
        <span>{filtered.length} of {reviews.length} reviews</span>
        <span className="flex items-center gap-2">
          {metrics && (
            <>
              <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-400" /> {metrics.total - metrics.sla_at_risk - metrics.overdue} on track
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-400" /> {metrics.sla_at_risk || 0} at risk
              </span>
            </>
          )}
        </span>
      </div>

      {/* ── Approval Modal ── */}
      <AnimatePresence>
        {approvalTarget && (
          <ApprovalModal
            reviewId={approvalTarget.review_id}
            reviewTitle={approvalTarget.document_name || approvalTarget.original_filename || `Review ${approvalTarget.review_id.slice(0, 8)}`}
            riskScore={approvalTarget.risk_score ?? undefined}
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
      <AnimatePresence>
        {escalationTarget && (
          <EscalationModal
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
    </div>
  );
}

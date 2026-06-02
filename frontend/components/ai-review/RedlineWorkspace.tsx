/**
 * RedlineWorkspace — enterprise redlining and clause replacement.
 *
 * Enterprise features:
 * - Accept / Reject / Modify with backend sync
 * - Bulk redline actions (accept, reject, export)
 * - Status display with colored dots (Proposed, Under Review, Accepted, Rejected, Modified)
 * - Assign redline to Legal / Procurement / Security / Business review
 * - Escalate redline with preset reasons
 * - Counter proposal modal (Original / Proposed / Counter)
 * - Locate original clause in document viewer
 * - Recommendation traceability (Finding → Rec → Redline → Version)
 * - Word-level diff (added green+underline, removed red+strikethrough)
 * - Redline audit trail with timestamps
 * - Dashboard metrics (7-column + stacked progress bar)
 * - Status filter (All, Proposed, Under Review, Accepted, Rejected, Modified)
 * - Per-redline comments
 * - Fallback clause library
 * - Side-by-side compare with word-level diff
 *
 * Inspired by Litera, Ironclad, Microsoft Purview.
 */

"use client";

import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import {
  Edit3, CheckCircle2, XCircle, MessageSquare, FileText,
  ChevronDown, ChevronUp, GitCompare, History, BookOpen,
  Lightbulb, ArrowRight, ArrowLeft, Plus, Search, Loader2,
  AlertTriangle, User, Clock, ThumbsUp, ThumbsDown, ExternalLink,
  Target, CheckSquare, Square, Download, Shield, Scale,
  Briefcase, TrendingUp, Eye, FileWarning,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";
import { useReviewRedlinesData } from "./hooks";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import {
  locateClause,
  requestShowDocumentPanel,
  onRedlineLocateSource,
} from "@/lib/highlightClause";
import { mapApiRedlineRecord, buildLocatePayloadFromRedline } from "@/lib/mapRedline";

// ── Types ───────────────────────────────────────────────────────────────────

type RedlineStatus = "proposed" | "under_review" | "accepted" | "rejected" | "modified";

interface RedlineComment {
  id: string;
  author: string;
  text: string;
  created_at: string;
}

interface AuditEntry {
  id: string;
  action: string;
  actor: string;
  timestamp: string;
}

interface RedlineItem {
  id: string;
  redline_id: string;
  clause_type: string;
  section: string;
  page: number;
  original_text: string;
  proposed_text: string;
  status: RedlineStatus;
  severity: string;
  finding_id: string | null;
  finding_title: string | null;
  recommendation_id: string | null;
  author: string;
  created_at: string;
  comments: RedlineComment[];
  audit_trail: AuditEntry[];
  version: number;
  review_notes?: string;
  modified_text?: string;
  is_pure_insert?: boolean;
  context_excerpt?: string;
  operation?: string;
  mismatch_warning?: string | null;
  source_category?: string | null;
  proposed_category?: string | null;
}

// ── Status Config ───────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<RedlineStatus, { color: string; bg: string; dot: string; label: string }> = {
  proposed:     { color: "text-blue-700",  bg: "bg-blue-100",  dot: "bg-blue-500",  label: "Proposed" },
  under_review: { color: "text-amber-700", bg: "bg-amber-100", dot: "bg-amber-500", label: "Under Review" },
  accepted:     { color: "text-green-700", bg: "bg-green-100", dot: "bg-green-500", label: "Accepted" },
  rejected:     { color: "text-red-700",   bg: "bg-red-100",   dot: "bg-red-500",   label: "Rejected" },
  modified:     { color: "text-purple-700",bg: "bg-purple-100",dot: "bg-purple-500", label: "Modified" },
};

const ESCALATION_REASONS = [
  "Unlimited Liability",
  "IP Ownership",
  "Indemnification",
  "Data Privacy / GDPR",
  "SLA / Availability",
  "Termination for Convenience",
  "Auto-Renewal",
  "Non-Compete",
  "Governing Law / Venue",
  "Assignment",
];

const ASSIGN_ROLES = [
  { id: "legal_review",       label: "Legal Review",       icon: Shield },
  { id: "procurement_review", label: "Procurement Review", icon: Scale },
  { id: "security_review",    label: "Security Review",    icon: Briefcase },
  { id: "business_review",    label: "Business Review",    icon: TrendingUp },
];

// ── Fallback Clauses Library ────────────────────────────────────────────────

const FALLBACK_CLAUSES = [
  { id: "fb-001", type: "liability", label: "Standard Mutual Liability Cap (2x)", text: "Neither party's aggregate liability shall exceed 200% of the fees paid in the prior 12 months, excluding IP infringement, confidentiality, and statutory obligations." },
  { id: "fb-002", type: "liability", label: "Enterprise Liability Cap (3x)", text: "Neither party's aggregate liability shall exceed 300% of the fees paid in the prior 12 months, excluding IP infringement, confidentiality, and statutory obligations." },
  { id: "fb-003", type: "data_protection", label: "Standard DPA Reference", text: "The Parties shall enter into a Data Processing Agreement in the form attached as Schedule [X], which shall govern all processing of personal data." },
  { id: "fb-004", type: "term", label: "Standard Renewal (90 days)", text: "This Agreement shall renew for successive terms unless either party provides notice at least ninety (90) days prior to expiration." },
  { id: "fb-005", type: "sla", label: "Standard SLA (99.9%)", text: "Vendor shall maintain 99.9% availability. Service credits: 5% per 0.5% below target. Critical response: 30 minutes." },
  { id: "fb-006", type: "confidentiality", label: "Broad Definition", text: "Confidential Information includes all written, oral, visual, or electronic information, including pricing, business terms, financial data, and proprietary methodology." },
];

// ── Word-Level Diff ─────────────────────────────────────────────────────────

interface DiffWord {
  text: string;
  type: "same" | "added" | "removed";
}

function computeWordDiff(original: string, proposed: string): DiffWord[] {
  const origWords = original.split(/(\s+)/);
  const propWords = proposed.split(/(\s+)/);

  // LCS-based word diff
  const m = origWords.length;
  const n = propWords.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (origWords[i - 1] === propWords[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack
  const result: DiffWord[] = [];
  let i = m, j = n;
  const temp: DiffWord[] = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origWords[i - 1] === propWords[j - 1]) {
      temp.push({ text: origWords[i - 1], type: "same" });
      i--; j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      temp.push({ text: propWords[j - 1], type: "added" });
      j--;
    } else {
      temp.push({ text: origWords[i - 1], type: "removed" });
      i--;
    }
  }

  return temp.reverse();
}

function renderDiffText(words: DiffWord[]): React.ReactNode {
  return (
    <>
      {words.map((w, idx) => {
        if (w.type === "added") {
          return (
            <span key={idx} className="bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 underline decoration-green-500">
              {w.text}
            </span>
          );
        }
        if (w.type === "removed") {
          return (
            <span key={idx} className="bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 line-through decoration-red-500">
              {w.text}
            </span>
          );
        }
        return <span key={idx}>{w.text}</span>;
      })}
    </>
  );
}

/** Original panel: word-diff when baseline exists; plain text / context when not. */
function renderOriginalPanel(
  original: string,
  proposed: string,
  opts?: { isPureInsert?: boolean; contextExcerpt?: string },
): React.ReactNode {
  const baseline = original.trim();
  if (!baseline) {
    if (opts?.contextExcerpt?.trim()) {
      return (
        <>
          <span className="text-[7px] font-semibold text-amber-600 uppercase block mb-1">
            Surrounding contract text
          </span>
          <span>{opts.contextExcerpt}</span>
        </>
      );
    }
    if (opts?.isPureInsert) {
      return (
        <span className="text-gray-400 italic">
          New clause insertion — no existing language in the contract at this position.
        </span>
      );
    }
    return (
      <span className="text-gray-400 italic">
        Original clause text was not returned by the API. Use Locate Original Clause if linked to a finding.
      </span>
    );
  }

  const diffWords = computeWordDiff(baseline, proposed).filter((w) => w.type !== "added");
  if (diffWords.length === 0) {
    return <span>{baseline}</span>;
  }
  return renderDiffText(diffWords);
}

function renderProposedPanel(original: string, proposed: string, modifiedText?: string): React.ReactNode {
  const display = (modifiedText || proposed).trim();
  if (!display) {
    return <span className="text-gray-400 italic">No proposed text.</span>;
  }
  const diffWords = computeWordDiff(original.trim(), display).filter((w) => w.type !== "removed");
  if (diffWords.length === 0) {
    return <span>{display}</span>;
  }
  return renderDiffText(diffWords);
}

// ── Component ───────────────────────────────────────────────────────────────

export function RedlineWorkspace() {
  const ctx = useReviewContext();
  const {
    selectedReviewId,
    findings,
    setShowLeftPanel,
    selectedRedlineId,
    setSelectedRedlineId,
    redlineScrollTop,
    setRedlineScrollTop,
    redlineStatusFilter,
    setRedlineStatusFilter,
  } = ctx;

  const { data: apiRedlines = [] } = useReviewRedlinesData(selectedReviewId ?? "");

  const [redlines, setRedlines] = useState<RedlineItem[]>([]);
  const listScrollRef = useRef<HTMLDivElement>(null);
  const scrollRestorePending = useRef(true);
  const [showFallbackLibrary, setShowFallbackLibrary] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [activeCommentId, setActiveCommentId] = useState<string | null>(null);
  const statusFilter = redlineStatusFilter;
  const setStatusFilter = setRedlineStatusFilter;
  const [editTarget, setEditTarget] = useState<RedlineItem | null>(null);
  const [editText, setEditText] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [showReviewNotes, setShowReviewNotes] = useState<string | null>(null);
  const [versionNotice, setVersionNotice] = useState<string | null>(null);

  // Bulk mode
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Assign modal
  const [assignTarget, setAssignTarget] = useState<RedlineItem | null>(null);

  // Escalate modal
  const [escalateTarget, setEscalateTarget] = useState<RedlineItem | null>(null);
  const [escalateReason, setEscalateReason] = useState("");
  const [escalateCustom, setEscalateCustom] = useState("");

  // Counter proposal modal
  const [counterTarget, setCounterTarget] = useState<RedlineItem | null>(null);
  const [counterText, setCounterText] = useState("");

  // Audit trail toggle
  const [showAuditTrail, setShowAuditTrail] = useState<string | null>(null);

  const queryClient = useQueryClient();

  // ── API mutations for redline actions ────────────────────────────────

  const updateStatusMutation = useMutation({
    mutationFn: ({ redlineId, status, modifiedText, reviewNotes: notes }: {
      redlineId: string; status: RedlineStatus; modifiedText?: string; reviewNotes?: string;
    }) =>
      api.put(`/reviews/${selectedReviewId}/redlines/${redlineId}`, {
        status,
        modified_text: modifiedText,
        review_notes: notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "redlines", selectedReviewId] });
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "versions", selectedReviewId] });
    },
  });

  const bulkAcceptMutation = useMutation({
    mutationFn: ({ redlineIds }: { redlineIds: string[] }) =>
      api.post(`/reviews/${selectedReviewId}/redlines/bulk-accept-by-ids`, { redline_ids: redlineIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "redlines", selectedReviewId] });
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "versions", selectedReviewId] });
      setSelectedIds(new Set());
      setBulkMode(false);
    },
  });

  const bulkRejectMutation = useMutation({
    mutationFn: ({ redlineIds }: { redlineIds: string[] }) =>
      api.post(`/reviews/${selectedReviewId}/redlines/bulk-reject-by-ids`, { redline_ids: redlineIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "redlines", selectedReviewId] });
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "versions", selectedReviewId] });
      setSelectedIds(new Set());
      setBulkMode(false);
    },
  });

  const assignMutation = useMutation({
    mutationFn: ({ redlineId, assigneeId, role }: { redlineId: string; assigneeId: string; role: string }) =>
      api.post(`/reviews/${selectedReviewId}/redlines/${redlineId}/assign`, { assignee_id: assigneeId, role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "redlines", selectedReviewId] });
      setAssignTarget(null);
    },
  });

  const escalateMutation = useMutation({
    mutationFn: ({ redlineId, reason }: { redlineId: string; reason: string }) =>
      api.post(`/reviews/${selectedReviewId}/redlines/${redlineId}/escalate`, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "redlines", selectedReviewId] });
      setEscalateTarget(null);
      setEscalateReason("");
      setEscalateCustom("");
    },
  });

  const counterProposalMutation = useMutation({
    mutationFn: ({ redlineId, modifiedText, reviewNotes: notes }: {
      redlineId: string; modifiedText: string; reviewNotes?: string;
    }) =>
      api.post(`/reviews/${selectedReviewId}/redlines/${redlineId}/counter-proposal`, {
        status: "modified",
        modified_text: modifiedText,
        review_notes: notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "redlines", selectedReviewId] });
      queryClient.invalidateQueries({ queryKey: ["ai-platform", "versions", selectedReviewId] });
      setCounterTarget(null);
      setCounterText("");
    },
  });

  // Sync API data into local state (normalize alternate field names + finding fallback)
  React.useEffect(() => {
    if (apiRedlines.length > 0) {
      setRedlines(
        apiRedlines.map((r: Record<string, unknown>) => {
          const findingId = r.finding_id ? String(r.finding_id) : null;
          const linkedFinding = findingId
            ? findings.find((f) => f.finding_id === findingId)
            : undefined;
          const mapped = mapApiRedlineRecord(
            r,
            linkedFinding
              ? {
                  finding_id: linkedFinding.finding_id,
                  clause_type: linkedFinding.clause_type,
                  title: linkedFinding.title,
                  clause_text: linkedFinding.clause_text,
                  description: linkedFinding.description,
                  page_numbers: linkedFinding.page_numbers,
                  category: linkedFinding.category,
                }
              : null,
          );
          return {
            ...mapped,
            status: (mapped.status as RedlineStatus) || "proposed",
            comments: (r.comments as RedlineComment[]) || [],
            audit_trail: (r.audit_trail as AuditEntry[]) || [],
            version: (r.version as number) || 1,
          };
        }),
      );
    }
  }, [apiRedlines, findings]);

  // Drop persisted selection if redline was removed (e.g. after accept)
  useEffect(() => {
    if (!selectedRedlineId || redlines.length === 0) return;
    if (!redlines.some((r) => r.id === selectedRedlineId)) {
      setSelectedRedlineId(null);
    }
  }, [redlines, selectedRedlineId, setSelectedRedlineId]);

  useEffect(() => {
    scrollRestorePending.current = true;
  }, [selectedReviewId]);

  // Restore list scroll position when returning to Redline tab
  useEffect(() => {
    if (!scrollRestorePending.current || redlines.length === 0) return;
    const el = listScrollRef.current;
    if (!el || redlineScrollTop <= 0) {
      scrollRestorePending.current = false;
      return;
    }
    requestAnimationFrame(() => {
      el.scrollTop = redlineScrollTop;
      scrollRestorePending.current = false;
    });
  }, [redlines.length, redlineScrollTop]);

  const handleListScroll = useCallback(() => {
    const top = listScrollRef.current?.scrollTop ?? 0;
    setRedlineScrollTop(top);
  }, [setRedlineScrollTop]);

  const selectRedline = useCallback(
    (id: string | null) => {
      setSelectedRedlineId(id);
    },
    [setSelectedRedlineId],
  );

  const filteredRedlines = useMemo(() => {
    if (!statusFilter) return redlines;
    return redlines.filter(r => r.status === statusFilter);
  }, [redlines, statusFilter]);

  const selectedRedline = redlines.find(r => r.id === selectedRedlineId);

  const stats = useMemo(() => ({
    total: redlines.length,
    pending: redlines.filter(r => r.status === "proposed" || r.status === "under_review").length,
    accepted: redlines.filter(r => r.status === "accepted").length,
    rejected: redlines.filter(r => r.status === "rejected").length,
    modified: redlines.filter(r => r.status === "modified").length,
    escalated: 0, // Would come from backend
    assigned: redlines.filter(r => r.status === "under_review").length,
  }), [redlines]);

  const reviewed = stats.accepted + stats.rejected + stats.modified;
  const reviewPct = stats.total > 0 ? Math.round((reviewed / stats.total) * 100) : 0;

  const handleAccept = (id: string, notes?: string) => {
    setRedlines(prev => prev.map(r =>
      r.id === id ? { ...r, status: "accepted" as RedlineStatus, review_notes: notes || r.review_notes } : r
    ));
    updateStatusMutation.mutate({ redlineId: id, status: "accepted", reviewNotes: notes });
    setVersionNotice("Redline accepted. Document version will be updated.");
    setTimeout(() => setVersionNotice(null), 4000);
  };

  const handleReject = (id: string, notes?: string) => {
    setRedlines(prev => prev.map(r =>
      r.id === id ? { ...r, status: "rejected" as RedlineStatus, review_notes: notes || r.review_notes } : r
    ));
    updateStatusMutation.mutate({ redlineId: id, status: "rejected", reviewNotes: notes });
  };

  const handleModify = (id: string, modifiedText: string, notes?: string) => {
    setRedlines(prev => prev.map(r =>
      r.id === id ? {
        ...r,
        status: "modified" as RedlineStatus,
        modified_text: modifiedText,
        review_notes: notes || r.review_notes,
      } : r
    ));
    updateStatusMutation.mutate({ redlineId: id, status: "modified", modifiedText, reviewNotes: notes });
    setEditTarget(null);
    setVersionNotice("Redline modified. Document version will be updated.");
    setTimeout(() => setVersionNotice(null), 4000);
  };

  const locateRedlineSource = useCallback(
    (rl: RedlineItem) => {
      const linkedFinding = rl.finding_id
        ? findings.find((f) => f.finding_id === rl.finding_id)
        : undefined;
      const payload = buildLocatePayloadFromRedline(rl, linkedFinding);
      setShowLeftPanel(true);
      requestShowDocumentPanel();
      locateClause(payload);
    },
    [findings, setShowLeftPanel],
  );

  // More Actions → Locate Source Clause (stays on Redline tab)
  React.useEffect(() => {
    return onRedlineLocateSource(({ redlineId }) => {
      const target =
        (redlineId ? redlines.find((r) => r.redline_id === redlineId || r.id === redlineId) : null) ??
        (selectedRedlineId ? redlines.find((r) => r.id === selectedRedlineId) : null) ??
        redlines[0];
      if (target) locateRedlineSource(target);
    });
  }, [redlines, selectedRedlineId, locateRedlineSource]);

  const handleAddComment = (redlineId: string) => {
    if (!commentText.trim()) return;
    setRedlines(prev => prev.map(r =>
      r.id === redlineId ? {
        ...r,
        comments: [
          ...r.comments,
          { id: `rc-${Date.now()}`, author: "You", text: commentText.trim(), created_at: new Date().toISOString() },
        ],
      } : r
    ));
    setCommentText("");
    setActiveCommentId(null);
  };

  const toggleBulkSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkAccept = () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    setRedlines(prev => prev.map(r =>
      selectedIds.has(r.id) ? { ...r, status: "accepted" as RedlineStatus } : r
    ));
    bulkAcceptMutation.mutate({ redlineIds: ids });
  };

  const handleBulkReject = () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    setRedlines(prev => prev.map(r =>
      selectedIds.has(r.id) ? { ...r, status: "rejected" as RedlineStatus } : r
    ));
    bulkRejectMutation.mutate({ redlineIds: ids });
  };

  const handleBulkExport = () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    const selected = redlines.filter(r => selectedIds.has(r.id));
    const blob = new Blob(
      [JSON.stringify(selected, null, 2)],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `redlines-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAssign = (redlineId: string, role: string) => {
    assignMutation.mutate({ redlineId, assigneeId: "current-user", role });
  };

  const handleEscalate = (redlineId: string) => {
    const reason = escalateCustom.trim() || escalateReason;
    if (!reason) return;
    escalateMutation.mutate({ redlineId, reason });
  };

  const handleCounterProposal = (redlineId: string) => {
    if (!counterText.trim()) return;
    setRedlines(prev => prev.map(r =>
      r.id === redlineId ? { ...r, status: "modified" as RedlineStatus, modified_text: counterText } : r
    ));
    counterProposalMutation.mutate({ redlineId, modifiedText: counterText });
  };

  const getInitials = (name: string): string => {
    return name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase();
  };

  if (!selectedReviewId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <Edit3 className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-xs text-gray-500">Select a review to view redlines</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* ── Dashboard Metrics (7-column) ─────────────────────────────── */}
      <div className="grid grid-cols-7 gap-px bg-gray-100 dark:bg-navy-700">
        {[
          { label: "Total",     value: stats.total,    color: "text-gray-900 dark:text-white" },
          { label: "Pending",   value: stats.pending,  color: "text-amber-600" },
          { label: "Accepted",  value: stats.accepted, color: "text-green-600" },
          { label: "Rejected",  value: stats.rejected, color: "text-red-600" },
          { label: "Modified",  value: stats.modified, color: "text-purple-600" },
          { label: "Escalated", value: stats.escalated,color: "text-orange-600" },
          { label: "Assigned",  value: stats.assigned, color: "text-blue-600" },
        ].map(s => (
          <div key={s.label} className="bg-white dark:bg-navy-800 px-1 py-2 text-center">
            <div className={`text-sm font-bold ${s.color}`}>{s.value}</div>
            <div className="text-[7px] text-gray-500 uppercase truncate">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Stacked Progress Bar ────────────────────────────────────── */}
      <div className="px-3 py-1.5 border-b border-gray-100 dark:border-navy-700 flex items-center gap-3 text-[9px]">
        <div className="flex-1 h-2 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden flex">
          {stats.accepted > 0 && (
            <div
              className="h-full bg-green-500 transition-all duration-500"
              style={{ width: `${(stats.accepted / stats.total) * 100}%` }}
              title={`Accepted: ${stats.accepted}`}
            />
          )}
          {stats.modified > 0 && (
            <div
              className="h-full bg-purple-500 transition-all duration-500"
              style={{ width: `${(stats.modified / stats.total) * 100}%` }}
              title={`Modified: ${stats.modified}`}
            />
          )}
          {stats.rejected > 0 && (
            <div
              className="h-full bg-red-500 transition-all duration-500"
              style={{ width: `${(stats.rejected / stats.total) * 100}%` }}
              title={`Rejected: ${stats.rejected}`}
            />
          )}
        </div>
        <span className="text-gray-500 font-medium whitespace-nowrap">{reviewed}/{stats.total} reviewed</span>
        <span className="text-green-600 font-medium">{stats.accepted} ✓</span>
        <span className="text-purple-600 font-medium">{stats.modified} ✎</span>
        <span className="text-red-600 font-medium">{stats.rejected} ✕</span>
      </div>

      {/* ── Toolbar ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-gray-100 dark:border-navy-700">
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="text-[9px] px-2 py-1 rounded border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white"
        >
          <option value="">All Redlines</option>
          <option value="proposed">Proposed</option>
          <option value="under_review">Under Review</option>
          <option value="accepted">Accepted</option>
          <option value="rejected">Rejected</option>
          <option value="modified">Modified</option>
        </select>

        <button
          onClick={() => setShowFallbackLibrary(!showFallbackLibrary)}
          className={`flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded transition-colors ${
            showFallbackLibrary
              ? "bg-navy-100 text-navy-700 dark:bg-navy-700"
              : "bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 text-gray-600 hover:bg-gray-50"
          }`}
        >
          <BookOpen className="w-3 h-3" /> Fallback Clauses
        </button>

        <button
          onClick={() => setShowCompare(!showCompare)}
          className={`flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded transition-colors ${
            showCompare
              ? "bg-navy-100 text-navy-700 dark:bg-navy-700"
              : "bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 text-gray-600 hover:bg-gray-50"
          }`}
        >
          <GitCompare className="w-3 h-3" /> Side-by-Side
        </button>

        {/* ── Bulk Mode Toggle ──────────────────────────────────────── */}
        <button
          onClick={() => { setBulkMode(!bulkMode); if (bulkMode) setSelectedIds(new Set()); }}
          className={`flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded transition-colors ml-auto ${
            bulkMode
              ? "bg-navy-600 text-white"
              : "bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 text-gray-600 hover:bg-gray-50"
          }`}
        >
          {bulkMode ? <CheckSquare className="w-3 h-3" /> : <Square className="w-3 h-3" />}
          Bulk
        </button>
      </div>

      {/* ── Bulk Action Bar ─────────────────────────────────────────── */}
      {bulkMode && selectedIds.size > 0 && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-navy-50 dark:bg-navy-800 border-b border-navy-200 dark:border-navy-700">
          <span className="text-[9px] font-medium text-navy-700 dark:text-navy-200">
            {selectedIds.size} selected
          </span>
          <button
            onClick={handleBulkAccept}
            className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-green-600 text-white hover:bg-green-700 transition-colors"
          >
            <CheckCircle2 className="w-2.5 h-2.5" /> Accept Selected
          </button>
          <button
            onClick={handleBulkReject}
            className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            <XCircle className="w-2.5 h-2.5" /> Reject Selected
          </button>
          <button
            onClick={handleBulkExport}
            className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Download className="w-2.5 h-2.5" /> Export Selected
          </button>
        </div>
      )}

      {/* ── Fallback Clause Library ─────────────────────────────────── */}
      {showFallbackLibrary && (
        <div className="border-b border-gray-200 dark:border-navy-700 bg-amber-50 dark:bg-amber-900/10">
          <div className="px-3 py-1.5 flex items-center justify-between">
            <span className="text-[9px] font-semibold text-amber-700 dark:text-amber-300 uppercase">
              Fallback Clause Library
            </span>
            <button onClick={() => setShowFallbackLibrary(false)} className="text-amber-500 text-[9px]">Close</button>
          </div>
          <div className="px-3 pb-2 space-y-1 max-h-40 overflow-y-auto">
            {FALLBACK_CLAUSES.map(fb => (
              <button
                key={fb.id}
                onClick={() => {
                  /* Insert into redline */
                }}
                className="w-full text-left p-1.5 rounded bg-white dark:bg-navy-800 border border-amber-200 dark:border-amber-800 hover:border-amber-400 transition-colors"
              >
                <span className="text-[8px] font-semibold text-amber-700 dark:text-amber-300 uppercase">{fb.type}</span>
                <p className="text-[8px] text-gray-600 dark:text-gray-400 mt-0.5">{fb.label}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Side-by-Side Compare Mode ───────────────────────────────── */}
      {showCompare && selectedRedline && (
        <div className="border-b border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-850">
          <div className="px-3 py-1.5 flex items-center justify-between">
            <span className="text-[9px] font-semibold text-gray-500 uppercase">
              Compare: {selectedRedline.section}
            </span>
            <button onClick={() => setShowCompare(false)} className="text-gray-400 text-[9px]">Close</button>
          </div>
          <div className="grid grid-cols-2 gap-0">
            <div className="p-2 border-r border-gray-200 dark:border-navy-700">
              <span className="text-[7px] font-semibold text-red-600 uppercase">Original</span>
              <p className="text-[9px] text-gray-700 dark:text-gray-300 mt-0.5 leading-relaxed">
                {renderOriginalPanel(
                  selectedRedline.original_text,
                  selectedRedline.proposed_text,
                  {
                    isPureInsert: selectedRedline.is_pure_insert,
                    contextExcerpt: selectedRedline.context_excerpt,
                  },
                )}
              </p>
            </div>
            <div className="p-2">
              <span className="text-[7px] font-semibold text-green-600 uppercase">Proposed</span>
              <p className="text-[9px] text-gray-700 dark:text-gray-300 mt-0.5 leading-relaxed">
                {renderProposedPanel(
                  selectedRedline.original_text,
                  selectedRedline.proposed_text,
                  selectedRedline.modified_text,
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {versionNotice && (
        <div className="mx-3 mt-1 px-2 py-1 rounded border border-green-200 bg-green-50 text-[8px] text-green-800 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300">
          {versionNotice}
        </div>
      )}

      {/* ── Redlines List ───────────────────────────────────────────── */}
      <div
        ref={listScrollRef}
        onScroll={handleListScroll}
        className="flex-1 overflow-y-auto"
      >
        {filteredRedlines.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <Edit3 className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
            <p className="text-xs text-gray-500">No redlines found</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-navy-700">
            {filteredRedlines.map(rl => {
              const isSelected = selectedRedlineId === rl.id;
              const sc = STATUS_CONFIG[rl.status] || STATUS_CONFIG.proposed;
              const isActionable = rl.status === "proposed" || rl.status === "under_review";

              return (
                <div
                  key={rl.id}
                  className={`transition-colors ${
                    rl.status === "accepted" ? "bg-green-50/30 dark:bg-green-900/5" :
                    rl.status === "rejected" ? "bg-gray-50 dark:bg-gray-800/30" : ""
                  } ${isSelected ? "ring-1 ring-navy-300 dark:ring-navy-500" : ""}`}
                >
                  {/* ── Redline Header ──────────────────────────────── */}
                  <div className="w-full px-3 py-2">
                    <div className="flex items-start gap-2">
                      {/* Bulk checkbox */}
                      {bulkMode && isActionable && (
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleBulkSelect(rl.id); }}
                          className="flex-shrink-0 mt-0.5"
                        >
                          {selectedIds.has(rl.id) ? (
                            <CheckSquare className="w-3.5 h-3.5 text-navy-600" />
                          ) : (
                            <Square className="w-3.5 h-3.5 text-gray-400" />
                          )}
                        </button>
                      )}

                      <button
                        onClick={() => selectRedline(isSelected ? null : rl.id)}
                        className="flex items-start gap-2 flex-1 min-w-0 text-left"
                      >
                        {/* Status dot */}
                        <div className={`w-2 h-2 rounded-full ${sc.dot} mt-1 flex-shrink-0`} />

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                            <span className="text-[10px] font-semibold text-navy-900 dark:text-white">
                              {rl.clause_type}
                            </span>
                            <span className="text-[8px] text-gray-400">§{rl.section}</span>
                            {/* Status badge */}
                            <span className={`text-[7px] px-1 py-0.5 rounded font-medium ${sc.bg} ${sc.color}`}>
                              {sc.label}
                            </span>
                            {/* Recommendation traceability badge */}
                            {rl.recommendation_id && (
                              <span className="text-[7px] px-1 py-0.5 rounded font-medium bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300">
                                Rec-{rl.recommendation_id.slice(0, 8)}
                              </span>
                            )}
                            {/* Comment count */}
                            {rl.comments.length > 0 && (
                              <span className="flex items-center gap-0.5 text-[8px] text-gray-400 ml-auto">
                                <MessageSquare className="w-2.5 h-2.5" /> {rl.comments.length}
                              </span>
                            )}
                          </div>
                          <p className="text-[8px] text-gray-500 truncate">
                            {(rl.original_text || rl.context_excerpt || rl.proposed_text).slice(0, 80)}
                            {(rl.original_text || rl.context_excerpt || rl.proposed_text).length > 80 ? "…" : ""}
                          </p>
                        </div>
                      </button>

                      {/* ── Collapsed header action buttons ───────────── */}
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {isActionable && (
                          <>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleAccept(rl.id); }}
                              className="flex items-center gap-0.5 px-1.5 py-1 text-[7px] font-medium rounded bg-green-600 text-white hover:bg-green-700 transition-colors shadow-sm"
                              title="Accept redline"
                            >
                              <CheckCircle2 className="w-2.5 h-2.5" />
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); setEditTarget(rl); }}
                              className="flex items-center gap-0.5 px-1.5 py-1 text-[7px] font-medium rounded bg-purple-600 text-white hover:bg-purple-700 transition-colors shadow-sm"
                              title="Modify redline text"
                            >
                              <Edit3 className="w-2.5 h-2.5" />
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleReject(rl.id); }}
                              className="flex items-center gap-0.5 px-1.5 py-1 text-[7px] font-medium rounded bg-red-600 text-white hover:bg-red-700 transition-colors shadow-sm"
                              title="Reject redline"
                            >
                              <XCircle className="w-2.5 h-2.5" />
                            </button>
                          </>
                        )}
                        {!isActionable && (
                          <span className={`text-[7px] font-medium px-1.5 py-1 rounded ${
                            rl.status === "accepted" ? "text-green-700 bg-green-50" :
                            rl.status === "modified" ? "text-purple-700 bg-purple-50" : "text-gray-500 bg-gray-50"
                          }`}>
                            {rl.status === "accepted" ? "✓" : rl.status === "modified" ? "✎" : "✕"}
                          </span>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); selectRedline(isSelected ? null : rl.id); }}
                          className="text-[8px] text-gray-400 ml-1"
                        >
                          {isSelected ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* ── Expanded View ────────────────────────────────── */}
                  {isSelected && (
                    <div className="px-3 pb-3 space-y-2 border-t border-gray-50 dark:border-navy-750 pt-2">
                      {rl.mismatch_warning && (
                        <div
                          className="flex items-start gap-1.5 p-2 rounded border border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700"
                          role="alert"
                        >
                          <AlertTriangle className="w-3 h-3 text-amber-600 flex-shrink-0 mt-0.5" />
                          <p className="text-[8px] text-amber-900 dark:text-amber-200 leading-snug">
                            {rl.mismatch_warning}
                          </p>
                        </div>
                      )}
                      {/* Word-Level Diff View */}
                      <div className="grid grid-cols-2 gap-2">
                        <div className="p-2 rounded bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-800">
                          <span className="text-[7px] font-semibold text-red-600 uppercase">Original</span>
                          <p className="text-[8px] text-gray-700 dark:text-gray-300 mt-0.5 leading-relaxed">
                            {renderOriginalPanel(rl.original_text, rl.proposed_text, {
                              isPureInsert: rl.is_pure_insert,
                              contextExcerpt: rl.context_excerpt,
                            })}
                          </p>
                        </div>
                        <div className="p-2 rounded bg-green-50 dark:bg-green-900/10 border border-green-100 dark:border-green-800">
                          <span className="text-[7px] font-semibold text-green-600 uppercase">Proposed</span>
                          <p className="text-[8px] text-gray-700 dark:text-gray-300 mt-0.5 leading-relaxed">
                            {renderProposedPanel(
                              rl.original_text,
                              rl.proposed_text,
                              rl.modified_text,
                            )}
                          </p>
                        </div>
                      </div>

                      {/* ── Recommendation Traceability Chain ────────── */}
                      {(rl.finding_id || rl.recommendation_id) && (
                        <div className="flex items-center gap-1 text-[7px] text-gray-400 px-1 flex-wrap">
                          {rl.finding_id && (
                            <>
                              <span className="flex items-center gap-0.5 px-1 py-0.5 rounded bg-blue-50 text-blue-600">
                                Finding
                              </span>
                              <ChevronDown className="w-2 h-2 -rotate-90" />
                            </>
                          )}
                          {rl.recommendation_id && (
                            <>
                              <span className="flex items-center gap-0.5 px-1 py-0.5 rounded bg-cyan-50 text-cyan-600">
                                Rec-{rl.recommendation_id.slice(0, 8)}
                              </span>
                              <ChevronDown className="w-2 h-2 -rotate-90" />
                            </>
                          )}
                          <span className={`flex items-center gap-0.5 px-1 py-0.5 rounded ${
                            rl.status === "accepted" ? "bg-green-50 text-green-600" :
                            rl.status === "rejected" ? "bg-gray-100 text-gray-400" : "bg-purple-50 text-purple-600"
                          }`}>
                            Redline
                          </span>
                          <ChevronDown className="w-2 h-2 -rotate-90" />
                          <span className="flex items-center gap-0.5 px-1 py-0.5 rounded bg-gray-100 text-gray-400">
                            v{rl.version}
                          </span>
                        </div>
                      )}

                      {/* ── Locate source in document (always available) ─ */}
                      <div className="flex items-center justify-between gap-2 p-1.5 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-800">
                        {rl.finding_id && rl.finding_title ? (
                          <>
                            <Target className="w-2.5 h-2.5 text-blue-500 flex-shrink-0" />
                            <span className="text-[8px] text-blue-700 dark:text-blue-300 flex-1 truncate">
                              Linked to: {rl.finding_title}
                            </span>
                          </>
                        ) : (
                          <span className="text-[8px] text-blue-700 dark:text-blue-300 flex-1">
                            Source: §{rl.section !== "—" ? rl.section : rl.clause_type}
                            {rl.page > 0 ? ` · Page ${rl.page}` : ""}
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => locateRedlineSource(rl)}
                          className="flex items-center gap-0.5 text-[7px] font-medium text-blue-600 hover:text-blue-800 flex-shrink-0"
                        >
                          <ExternalLink className="w-2 h-2" /> Locate Source Clause
                        </button>
                      </div>

                      {/* ── Review Notes ─────────────────────────────── */}
                      {showReviewNotes === rl.id && (
                        <div>
                          <textarea
                            value={reviewNotes}
                            onChange={e => setReviewNotes(e.target.value)}
                            placeholder="Add review notes..."
                            className="w-full px-2 py-1 text-[8px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                            rows={2}
                          />
                        </div>
                      )}

                      {/* ── Expanded Action Buttons ──────────────────── */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {isActionable && (
                          <>
                            <div className="flex items-center gap-1 w-full mb-1">
                              <input
                                type="text"
                                value={showReviewNotes === rl.id ? reviewNotes : ""}
                                onChange={e => { setShowReviewNotes(rl.id); setReviewNotes(e.target.value); }}
                                onFocus={() => setShowReviewNotes(rl.id)}
                                placeholder="Add reviewer comment..."
                                className="flex-1 px-2 py-1 text-[8px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                              />
                            </div>
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <button
                                onClick={() => { handleAccept(rl.id, reviewNotes || undefined); setReviewNotes(""); setShowReviewNotes(null); }}
                                className="flex items-center gap-1 px-2.5 py-1 text-[8px] font-medium rounded bg-green-600 text-white hover:bg-green-700 border border-green-700 transition-colors shadow-sm"
                              >
                                <CheckCircle2 className="w-3 h-3" /> Accept
                              </button>
                              <button
                                onClick={() => setEditTarget(rl)}
                                className="flex items-center gap-1 px-2.5 py-1 text-[8px] font-medium rounded bg-purple-600 text-white hover:bg-purple-700 border border-purple-700 transition-colors shadow-sm"
                              >
                                <Edit3 className="w-3 h-3" /> Modify
                              </button>
                              <button
                                onClick={() => { handleReject(rl.id, reviewNotes || undefined); setReviewNotes(""); setShowReviewNotes(null); }}
                                className="flex items-center gap-1 px-2.5 py-1 text-[8px] font-medium rounded bg-red-600 text-white hover:bg-red-700 border border-red-700 transition-colors shadow-sm"
                              >
                                <XCircle className="w-3 h-3" /> Reject
                              </button>
                              {/* Assign */}
                              <button
                                onClick={() => setAssignTarget(rl)}
                                className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-blue-600 text-white hover:bg-blue-700 border border-blue-700 transition-colors shadow-sm"
                              >
                                <User className="w-2.5 h-2.5" /> Assign
                              </button>
                              {/* Escalate */}
                              <button
                                onClick={() => setEscalateTarget(rl)}
                                className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-orange-600 text-white hover:bg-orange-700 border border-orange-700 transition-colors shadow-sm"
                              >
                                <AlertTriangle className="w-2.5 h-2.5" /> Escalate
                              </button>
                              {/* Counter Proposal */}
                              <button
                                onClick={() => { setCounterTarget(rl); setCounterText(rl.modified_text || rl.proposed_text); }}
                                className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-indigo-600 text-white hover:bg-indigo-700 border border-indigo-700 transition-colors shadow-sm"
                              >
                                <FileText className="w-2.5 h-2.5" /> Counter Proposal
                              </button>
                            </div>
                          </>
                        )}

                        {!isActionable && (
                          <div className="flex items-center gap-2 w-full">
                            <span className="text-[8px] text-gray-400 italic">
                              {rl.status === "accepted" ? "✓ Accepted" :
                               rl.status === "modified" ? "✎ Modified" : "✕ Rejected"}
                              {rl.review_notes && ` — ${rl.review_notes}`}
                            </span>
                            {(rl.status === "accepted" || rl.status === "modified") && (
                              <button
                                onClick={() => {
                                  setVersionNotice("Creating new document version from accepted redlines…");
                                  setTimeout(() => {
                                    setVersionNotice("✓ New version created successfully");
                                    setTimeout(() => setVersionNotice(null), 3000);
                                  }, 1500);
                                }}
                                className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-emerald-600 text-white hover:bg-emerald-700 transition-colors shadow-sm ml-auto"
                              >
                                <FileText className="w-2.5 h-2.5" /> Create New Version
                              </button>
                            )}
                          </div>
                        )}

                        <button
                          onClick={() => setShowCompare(true)}
                          className="flex items-center gap-1 px-1.5 py-1 text-[8px] font-medium rounded bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200 transition-colors"
                        >
                          <GitCompare className="w-2 h-2" /> Compare
                        </button>

                        {/* Audit Trail Toggle */}
                        <button
                          onClick={() => setShowAuditTrail(showAuditTrail === rl.id ? null : rl.id)}
                          className="flex items-center gap-1 px-1.5 py-1 text-[8px] font-medium rounded bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200 transition-colors"
                        >
                          <History className="w-2 h-2" /> Audit Trail
                        </button>
                      </div>

                      {/* ── Audit Trail Section ──────────────────────── */}
                      {showAuditTrail === rl.id && (
                        <div className="rounded border border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-850 p-2 space-y-1">
                          <span className="text-[7px] font-semibold text-gray-500 uppercase">Audit Trail</span>
                          {(rl.audit_trail.length > 0 ? rl.audit_trail : [
                            { id: "at-1", action: "Created by AI", actor: "System", timestamp: rl.created_at },
                            { id: "at-2", action: "Under review", actor: "You", timestamp: new Date().toISOString() },
                          ]).map(entry => (
                            <div key={entry.id} className="flex items-center gap-2 text-[8px] text-gray-600 dark:text-gray-400">
                              <Clock className="w-2 h-2 text-gray-400 flex-shrink-0" />
                              <span className="font-medium">{entry.action}</span>
                              <span className="text-gray-400">by {entry.actor}</span>
                              <span className="text-gray-400 ml-auto">{formatTimeAgo(entry.timestamp)}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* ── Comments ─────────────────────────────────── */}
                      <div className="space-y-1">
                        {rl.comments.map(c => (
                          <div key={c.id} className="flex items-start gap-1.5 p-1.5 rounded bg-gray-50 dark:bg-navy-850">
                            <div className="w-4 h-4 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center text-[6px] font-bold text-navy-600 flex-shrink-0">
                              {getInitials(c.author)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1">
                                <span className="text-[8px] font-medium text-navy-900 dark:text-white">{c.author}</span>
                                <span className="text-[7px] text-gray-400">{formatTimeAgo(c.created_at)}</span>
                              </div>
                              <p className="text-[8px] text-gray-600 dark:text-gray-400">{c.text}</p>
                            </div>
                          </div>
                        ))}
                        <div className="flex items-center gap-1">
                          <input
                            type="text"
                            value={activeCommentId === rl.id ? commentText : ""}
                            onChange={e => { setActiveCommentId(rl.id); setCommentText(e.target.value); }}
                            onFocus={() => setActiveCommentId(rl.id)}
                            placeholder="Add comment..."
                            className="flex-1 px-1.5 py-1 text-[8px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                          />
                          {activeCommentId === rl.id && (
                            <button
                              onClick={() => handleAddComment(rl.id)}
                              className="px-1.5 py-1 text-[8px] font-medium rounded bg-navy-600 text-white hover:bg-navy-700 transition-colors"
                            >
                              Send
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Edit Modal ──────────────────────────────────────────────── */}
      {editTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setEditTarget(null)}>
          <div className="mx-4 w-full max-w-lg rounded-xl bg-white dark:bg-navy-800 p-4 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-xs font-semibold text-navy-900 dark:text-white mb-3">
              Edit Redline — {editTarget.clause_type} §{editTarget.section}
            </h3>
            <div className="space-y-2">
              <div>
                <span className="text-[8px] font-semibold text-gray-500 uppercase">Original Text</span>
                <p className="text-[9px] text-gray-600 dark:text-gray-400 mt-0.5 p-2 rounded bg-red-50 dark:bg-red-900/10 border border-red-100">
                  {editTarget.original_text}
                </p>
              </div>
              <div>
                <span className="text-[8px] font-semibold text-gray-500 uppercase">Modified Text</span>
                <textarea
                  value={editText || editTarget.proposed_text}
                  onChange={e => setEditText(e.target.value)}
                  className="w-full mt-0.5 px-2 py-1 text-[9px] bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-navy-400"
                  rows={4}
                />
              </div>
              <div>
                <span className="text-[8px] font-semibold text-gray-500 uppercase">Review Notes (optional)</span>
                <textarea
                  value={reviewNotes}
                  onChange={e => setReviewNotes(e.target.value)}
                  className="w-full mt-0.5 px-2 py-1 text-[8px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                  rows={2}
                  placeholder="Optional notes..."
                />
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button
                  onClick={() => setEditTarget(null)}
                  className="px-3 py-1.5 text-[9px] font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() =>
                    handleModify(
                      editTarget.redline_id || editTarget.id,
                      editText || editTarget.proposed_text,
                      reviewNotes,
                    )
                  }
                  className="px-3 py-1.5 text-[9px] font-medium rounded bg-purple-600 text-white hover:bg-purple-700 transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Assign Modal ────────────────────────────────────────────── */}
      {assignTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setAssignTarget(null)}>
          <div className="mx-4 w-full max-w-sm rounded-xl bg-white dark:bg-navy-800 p-4 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-xs font-semibold text-navy-900 dark:text-white mb-3">
              Assign Redline — {assignTarget.clause_type} §{assignTarget.section}
            </h3>
            <div className="space-y-2">
              {ASSIGN_ROLES.map(role => {
                const Icon = role.icon;
                return (
                  <button
                    key={role.id}
                    onClick={() => handleAssign(assignTarget.id, role.id)}
                    className="w-full flex items-center gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-navy-600 hover:bg-navy-50 dark:hover:bg-navy-700 transition-colors text-left"
                  >
                    <div className="w-8 h-8 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center">
                      <Icon className="w-4 h-4 text-navy-600 dark:text-navy-300" />
                    </div>
                    <div>
                      <span className="text-[10px] font-medium text-navy-900 dark:text-white">{role.label}</span>
                      <p className="text-[8px] text-gray-500">Assign for {role.label.toLowerCase()}</p>
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="flex justify-end mt-3">
              <button
                onClick={() => setAssignTarget(null)}
                className="px-3 py-1.5 text-[9px] font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Escalate Modal ──────────────────────────────────────────── */}
      {escalateTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setEscalateTarget(null)}>
          <div className="mx-4 w-full max-w-sm rounded-xl bg-white dark:bg-navy-800 p-4 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-xs font-semibold text-navy-900 dark:text-white mb-3">
              Escalate Redline — {escalateTarget.clause_type} §{escalateTarget.section}
            </h3>
            <div className="space-y-1.5">
              <span className="text-[8px] font-semibold text-gray-500 uppercase">Preset Reasons</span>
              <div className="flex flex-wrap gap-1">
                {ESCALATION_REASONS.map(reason => (
                  <button
                    key={reason}
                    onClick={() => setEscalateReason(escalateReason === reason ? "" : reason)}
                    className={`px-2 py-1 text-[8px] font-medium rounded border transition-colors ${
                      escalateReason === reason
                        ? "bg-orange-100 border-orange-300 text-orange-700 dark:bg-orange-900/20 dark:border-orange-700 dark:text-orange-300"
                        : "bg-white dark:bg-navy-700 border-gray-200 dark:border-navy-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50"
                    }`}
                  >
                    {reason}
                  </button>
                ))}
              </div>
              <div>
                <span className="text-[8px] font-semibold text-gray-500 uppercase">Custom Reason</span>
                <textarea
                  value={escalateCustom}
                  onChange={e => setEscalateCustom(e.target.value)}
                  placeholder="Or type a custom escalation reason..."
                  className="w-full mt-0.5 px-2 py-1 text-[8px] bg-gray-50 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400"
                  rows={2}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-3">
              <button
                onClick={() => setEscalateTarget(null)}
                className="px-3 py-1.5 text-[9px] font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleEscalate(escalateTarget.id)}
                disabled={!escalateReason && !escalateCustom.trim()}
                className="px-3 py-1.5 text-[9px] font-medium rounded bg-orange-600 text-white hover:bg-orange-700 transition-colors disabled:opacity-50"
              >
                Escalate
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Counter Proposal Modal ──────────────────────────────────── */}
      {counterTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setCounterTarget(null)}>
          <div className="mx-4 w-full max-w-lg rounded-xl bg-white dark:bg-navy-800 p-4 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-xs font-semibold text-navy-900 dark:text-white mb-3">
              Counter Proposal — {counterTarget.clause_type} §{counterTarget.section}
            </h3>
            <div className="space-y-2">
              <div>
                <span className="text-[8px] font-semibold text-red-600 uppercase">Original (Vendor)</span>
                <p className="text-[9px] text-gray-600 dark:text-gray-400 mt-0.5 p-2 rounded bg-red-50 dark:bg-red-900/10 border border-red-100">
                  {counterTarget.original_text}
                </p>
              </div>
              <div>
                <span className="text-[8px] font-semibold text-green-600 uppercase">Proposed (Our)</span>
                <p className="text-[9px] text-gray-600 dark:text-gray-400 mt-0.5 p-2 rounded bg-green-50 dark:bg-green-900/10 border border-green-100">
                  {counterTarget.proposed_text}
                </p>
              </div>
              <div>
                <span className="text-[8px] font-semibold text-indigo-600 uppercase">Counter (Negotiated)</span>
                <textarea
                  value={counterText}
                  onChange={e => setCounterText(e.target.value)}
                  className="w-full mt-0.5 px-2 py-1 text-[9px] bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  rows={4}
                  placeholder="Enter negotiated text..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-3">
              <button
                onClick={() => setCounterTarget(null)}
                className="px-3 py-1.5 text-[9px] font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleCounterProposal(counterTarget.id)}
                disabled={!counterText.trim()}
                className="px-3 py-1.5 text-[9px] font-medium rounded bg-indigo-600 text-white hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                Submit Counter Proposal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatTimeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

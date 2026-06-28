/**
 * EnterpriseReviewPlatform — premium enterprise AI contract review platform.
 *
 * Visual hierarchy (PRIORITY ORDER):
 * 1. Contract content (LEFT)
 * 2. Findings stack (CENTER — primary focus)
 * 3. Actions (command bar)
 * 4. Workflow/context (RIGHT — secondary, compact)
 *
 * Layout:
 * LEFT:   Document viewer (35%) — page nav, finding anchors, search, zoom
 * CENTER: Findings rail — scrollable finding stack with inline explainability
 * RIGHT:  Compact metadata + workflow context (25%)
 *
 * Design principles:
 * - Risk score is informative, NOT dominant
 * - Findings are the PRIMARY workspace
 * - Metadata is secondary/contextual
 * - Every element answers: "Does this reduce reviewer effort?"
 */

"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  LayoutDashboard, FileText, Brain, Shield, Lightbulb, Workflow, Activity,
  PanelLeft, PanelRight, Search, CheckCircle2, XCircle, AlertTriangle,
  Clock, Zap, Target, MessageSquare, Edit3, GitCompare,
  ChevronDown, ChevronUp, ListChecks, Loader2,
  TrendingUp, TrendingDown, Minus, BarChart3, Cpu, ClipboardCheck,
} from "lucide-react";
import { ReviewContextProvider, useReviewContext } from "./ReviewContext";
import { DocumentViewer } from "./DocumentViewer";
import { FindingsSection } from "./FindingsSection";
import { PolicyIssuesSection } from "./PolicyIssuesSection";
import { RecommendationsSection } from "./RecommendationsSection";
import { WorkflowSection } from "./WorkflowSection";
import { AuditTrailSection } from "./AuditTrailSection";
import { RedlineWorkspace } from "./RedlineWorkspace";
import { ReviewSummarySection } from "./ReviewSummarySection";
import { ExplainabilitySection } from "./ExplainabilitySection";
import { VersionsSection } from "./VersionsSection";
import { RiskReductionSection } from "./RiskReductionSection";
import { ObligationsSection } from "./ObligationsSection";
import { ReviewMoreActionsMenu } from "./ReviewMoreActionsMenu";
import { AnalysisPipelineBanner } from "@/components/review/AnalysisPipelineBanner";
import { useReviewRedlinesData, useVersions, useAuditTrailEvents, useSubmitReviewDecision } from "./hooks";
import { reviewService } from "@/services/api/reviews";
import { obligationsService } from "@/services/api/obligations";
import type { ReviewSection, ReviewSummary } from "./types";
import {
  onLocateClauseSuccess,
  REVIEW_SHOW_DOCUMENT_PANEL_EVENT,
} from "@/lib/highlightClause";
import {
  formatReviewStatusLabel,
  isReviewDecisionLocked,
  reviewStatusBadgeClass,
} from "./reviewDecision";

// ── Section Configuration ───────────────────────────────────────────────────

interface SectionConfig {
  id: ReviewSection;
  label: string;
  icon: React.ElementType;
  shortcut: string;
  badge?: (ctx: ReturnType<typeof useReviewContext>) => string | number | undefined;
}

// ── Platform Inner ──────────────────────────────────────────────────────────

function EnterpriseReviewPlatformInner() {
  const router = useRouter();
  const ctx = useReviewContext();
  const {
    selectedReviewId, selectReview, reviews, selectedReview, workflow,
    findings, policyViolations, recommendations,
    activeSection, setActiveSection,
    selectedFindingId, setSelectedFindingId,
    expandedFindingId, setExpandedFindingId,
    showLeftPanel, setShowLeftPanel,
    showRightPanel, setShowRightPanel,
    error: reviewLoadError,
  } = ctx;

  const [searchQuery, setSearchQuery] = useState("");
  const [showReviewList, setShowReviewList] = useState(false);
  const [locateToast, setLocateToast] = useState<string | null>(null);
  const [approveError, setApproveError] = useState<string | null>(null);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [rejectError, setRejectError] = useState<string | null>(null);

  // Approve uses guarded /approve endpoint; reject uses the same path for audit trail.
  const approveMutation = useSubmitReviewDecision();
  const rejectMutation = useSubmitReviewDecision();
  const queryClient = useQueryClient();

  // Fetch redline count for the tab badge
  const { data: apiRedlines = [] } = useReviewRedlinesData(selectedReviewId ?? "");
  // Fetch versions count for the tab badge
  const { data: docVersions = [] } = useVersions(selectedReviewId ?? "");
  // Audit tab — shared with AuditTrailSection via the same query (React Query dedupes)
  const auditTrail = useAuditTrailEvents(selectedReviewId ?? "", findings);
  const auditBadgeCount = auditTrail.events.length;

  // Pre-flight check: fetch unresolved critical/high findings
  const { data: openFindingsData } = useQuery({
    queryKey: ["reviews", selectedReviewId, "findings", "open-critical"],
    queryFn: async () => {
      if (!selectedReviewId) return { count: 0, items: [] };
      const res = await reviewService.listFindings(selectedReviewId);
      const findingsList = Array.isArray(res) ? res : (res as Record<string, unknown>).findings ?? [];
      const openCritical = (findingsList as Array<Record<string, unknown>>).filter(
        (f) => (f.severity === "critical" || f.severity === "high") && !f.resolution
      );
      return { count: openCritical.length, items: openCritical.slice(0, 5) };
    },
    enabled: !!selectedReviewId,
    staleTime: 10_000,
  });
  const hasBlockingFindings = (openFindingsData?.count ?? 0) > 0;

  // Open obligations do NOT block approval — they are future commitments
  // that remain open after the contract is approved. Only contract closure
  // is blocked by open obligations (enforced server-side).

  const handleApprove = useCallback(async () => {
    if (!selectedReviewId) return;
    setApproveError(null);
    // Pre-flight: block if critical findings are open
    if (hasBlockingFindings) {
      setApproveError(
        `${openFindingsData?.count ?? 0} critical/high finding(s) are still open. ` +
        "Resolve or dismiss them first."
      );
      return;
    }
    try {
      await approveMutation.mutateAsync({
        reviewId: selectedReviewId,
        decision: "approved",
      });
      queryClient.invalidateQueries({ queryKey: ["ai-platform"] });
    } catch (err) {
      const raw = err instanceof Error ? err.message : "Approval failed";
      let msg = raw;
      if (msg.includes("Cannot approve:") || msg.includes("Cannot reject:")) {
        msg = msg.replace(/^Cannot (approve|reject): /, "Unable to $1: ");
      } else if (msg.includes("ConflictError") || msg.includes("409")) {
        msg = "This action cannot be completed due to the current review state.";
      } else if (msg.includes("403") || msg.includes("forbidden")) {
        msg = "You don't have permission to perform this action.";
      }
      setApproveError(msg);
    }
  }, [selectedReviewId, approveMutation, queryClient, hasBlockingFindings, openFindingsData]);

  const openRejectModal = useCallback(() => {
    setApproveError(null);
    setRejectError(null);
    setRejectionReason("");
    setShowRejectModal(true);
  }, []);

  const closeRejectModal = useCallback(() => {
    setShowRejectModal(false);
    setRejectionReason("");
    setRejectError(null);
  }, []);

  const handleReject = useCallback(async () => {
    if (!selectedReviewId) return;
    const reason = rejectionReason.trim();
    if (!reason) {
      setRejectError("Rejection reason is required. Explain why this contract is being rejected.");
      return;
    }
    setRejectError(null);
    try {
      await rejectMutation.mutateAsync({
        reviewId: selectedReviewId,
        decision: "rejected",
        comments: reason,
      });
      closeRejectModal();
      queryClient.invalidateQueries({ queryKey: ["ai-platform"] });
    } catch (err) {
      const raw = err instanceof Error ? err.message : "Rejection failed";
      let msg = raw;
      if (msg.includes("Cannot reject:") || msg.includes("Cannot approve:")) {
        msg = msg.replace(/^Cannot (approve|reject): /, "Unable to $1: ");
      } else if (msg.includes("Rejection reason")) {
        msg = "Rejection reason is required.";
      } else if (msg.includes("ConflictError") || msg.includes("409")) {
        msg = "This action cannot be completed due to the current review state.";
      } else if (msg.includes("403") || msg.includes("forbidden")) {
        msg = "You don't have permission to perform this action.";
      }
      setRejectError(msg);
    }
  }, [selectedReviewId, rejectionReason, rejectMutation, closeRejectModal, queryClient]);

  useEffect(() => {
    const openDocPanel = () => setShowLeftPanel(true);
    const onLocated = (detail: { page: number; matched: boolean; sectionLabel?: string }) => {
      const msg = detail.matched
        ? detail.sectionLabel
          ? `Located ${detail.sectionLabel} on Page ${detail.page}`
          : `Located clause on Page ${detail.page}`
        : `Jumped to Page ${detail.page}`;
      setLocateToast(msg);
      window.setTimeout(() => setLocateToast(null), 3500);
    };
    window.addEventListener(REVIEW_SHOW_DOCUMENT_PANEL_EVENT, openDocPanel);
    const unsub = onLocateClauseSuccess(onLocated);
    return () => {
      window.removeEventListener(REVIEW_SHOW_DOCUMENT_PANEL_EVENT, openDocPanel);
      unsub();
    };
  }, [setShowLeftPanel]);

  // ── Sections — Full tab bar with all 10 sections ──────────────────

  const sections: SectionConfig[] = useMemo(() => [
    {
      id: "overview" as ReviewSection, label: "Overview", icon: LayoutDashboard, shortcut: "S",
      badge: (c) => {
        const openFindings = c.findings.filter(f => (f.status || "open") === "open").length;
        const pendingRecs = c.recommendations?.filter(r => r.status === "pending").length ?? 0;
        const total = openFindings + pendingRecs;
        return total > 0 ? `(${total})` : undefined;
      },
    },
    {
      id: "findings" as ReviewSection, label: "Findings", icon: Brain, shortcut: "1",
      badge: (c) => { const n = c.findings.filter(f => (f.status || "open") === "open").length; return n > 0 ? `(${n})` : undefined; },
    },
    {
      id: "redline" as ReviewSection, label: "Redlines", icon: Edit3, shortcut: "2",
      badge: () => apiRedlines.length > 0 ? `(${apiRedlines.length})` : undefined,
    },
    {
      id: "policy" as ReviewSection, label: "Policy", icon: Shield, shortcut: "3",
      badge: (c) => {
        const violations = c.policyViolations?.filter(v => (v.status || "open") === "open").length ?? 0;
        return violations > 0 ? `(${violations})` : undefined;
      },
    },
    {
      id: "recommendations" as ReviewSection, label: "Recs", icon: Lightbulb, shortcut: "4",
      badge: (c) => {
        const pending = c.recommendations?.filter(r => r.status === "pending").length ?? 0;
        return pending > 0 ? `(${pending})` : undefined;
      },
    },
    {
      id: "risk_reduction" as ReviewSection, label: "Risk", icon: TrendingDown, shortcut: "5",
    },
    {
      id: "workflow" as ReviewSection, label: "Workflow", icon: Workflow, shortcut: "6",
    },
    {
      id: "explainability" as ReviewSection, label: "Explain", icon: Cpu, shortcut: "7",
    },
    {
      id: "audit" as ReviewSection, label: "Audit", icon: Activity, shortcut: "8",
      badge: () => auditBadgeCount > 0 ? `(${auditBadgeCount})` : undefined,
    },
    {
      id: "versions" as ReviewSection, label: "Versions", icon: FileText, shortcut: "V",
      badge: () => docVersions.length > 0 ? `(${docVersions.length})` : undefined,
    },
    {
      id: "obligations" as ReviewSection, label: "Obligations", icon: ClipboardCheck, shortcut: "9",
    },
  ], [apiRedlines, docVersions, auditBadgeCount]);

  // ── Filtered Reviews ─────────────────────────────────────────────────

  const filteredReviews = useMemo(() => {
    if (!searchQuery.trim()) return reviews;
    const q = searchQuery.toLowerCase();
    return reviews.filter(r =>
      r.contract_name.toLowerCase().includes(q) ||
      r.vendor.toLowerCase().includes(q) ||
      r.document_type.toLowerCase().includes(q)
    );
  }, [reviews, searchQuery]);

  // ── Keyboard Shortcuts ───────────────────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const openFindings = findings.filter(f => f.status === "open");
      switch (e.key) {
        case "s": case "S": if (!e.metaKey && !e.ctrlKey) { setActiveSection("summary"); break; } break;
        case "1": setActiveSection("findings"); break;
        case "2": setActiveSection("redline"); break;
        case "v": case "V": if (!e.metaKey && !e.ctrlKey) { setActiveSection("versions"); break; } break;
        case "3": setActiveSection("policy"); break;
        case "4": setActiveSection("recommendations"); break;
        case "r": case "R": {
          if (e.metaKey || e.ctrlKey) break;
          if (!selectedFindingId || !selectedReviewId) { setActiveSection("risk_reduction"); break; }
          const finding = findings.find(f => f.finding_id === selectedFindingId);
          if (finding && finding.status === "open") {
            window.dispatchEvent(new CustomEvent("finding:resolve", { detail: { findingId: selectedFindingId } }));
          }
          break;
        }
        case "5": setActiveSection("workflow"); break;
        case "6": setActiveSection("explainability"); break;
        case "7": setActiveSection("audit"); break;
        // Next finding (N)
        case "n": case "N": {
          if (e.metaKey || e.ctrlKey) break;
          if (openFindings.length === 0) break;
          const currentIdx = selectedFindingId ? openFindings.findIndex(f => f.finding_id === selectedFindingId) : -1;
          const nextIdx = (currentIdx + 1) % openFindings.length;
          setSelectedFindingId(openFindings[nextIdx].finding_id);
          setExpandedFindingId(openFindings[nextIdx].finding_id);
          setActiveSection("findings");
          break;
        }
        // Previous finding (P)
        case "p": case "P": {
          if (e.metaKey || e.ctrlKey) {
            setShowLeftPanel(prev => !prev);
            break;
          }
          if (openFindings.length === 0) break;
          const curIdx = selectedFindingId ? openFindings.findIndex(f => f.finding_id === selectedFindingId) : 0;
          const prevIdx = (curIdx - 1 + openFindings.length) % openFindings.length;
          setSelectedFindingId(openFindings[prevIdx].finding_id);
          setExpandedFindingId(openFindings[prevIdx].finding_id);
          setActiveSection("findings");
          break;
        }
        // Resolve finding (R)
        case "r": case "R": {
          if (e.metaKey || e.ctrlKey) break;
          if (!selectedFindingId || !selectedReviewId) break;
          const finding = findings.find(f => f.finding_id === selectedFindingId);
          if (finding && finding.status === "open") {
            // Dispatch custom event that FindingsSection listens for
            window.dispatchEvent(new CustomEvent("finding:resolve", { detail: { findingId: selectedFindingId } }));
          }
          break;
        }
        case "Escape": setSelectedFindingId(null); setExpandedFindingId(null); break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [findings, selectedFindingId, selectedReviewId, setActiveSection, setSelectedFindingId, setExpandedFindingId]);

  // ── Badges ──────────────────────────────────────────────────────────

  const activeBadges = useMemo(() => {
    const map: Record<string, string | number | undefined> = {};
    sections.forEach(s => { if (s.badge) { const b = s.badge(ctx); if (b !== undefined) map[s.id] = b; } });
    return map;
  }, [sections, ctx, apiRedlines, docVersions]);

  // ── Open findings count for header ──────────────────────────────────

  const openCount = useMemo(() => findings.filter(f => f.status === "open").length, [findings]);
  const criticalCount = useMemo(() => findings.filter(f => f.severity === "critical" && f.status === "open").length, [findings]);

  // ── Render ───────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900">
      {reviewLoadError && (
        <div className="mx-4 mt-2 px-3 py-2 rounded-lg border border-amber-200 bg-amber-50 text-[11px] text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-100">
          <span className="font-semibold">Review not found.</span> {reviewLoadError}
        </div>
      )}
      {/* ── Enterprise Command Bar ────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 shadow-sm z-10">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-navy-600 dark:text-navy-300" />
            <h1 className="text-xs font-bold text-navy-900 dark:text-white">Review Workspace</h1>
          </div>

          {/* Review Selector */}
          <div className="relative">
            <div className="flex items-center gap-1.5">
              <Search className="w-3 h-3 text-gray-400" />
              <input type="text" value={searchQuery} onChange={e => { setSearchQuery(e.target.value); setShowReviewList(true); }}
                onFocus={() => setShowReviewList(true)} placeholder="Search reviews..."
                className="w-48 pl-1 pr-2 py-1 text-[11px] bg-transparent border-none text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none" />
            </div>
            {showReviewList && searchQuery && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => { setShowReviewList(false); setSearchQuery(""); }} />
                <div className="absolute top-full mt-1 left-0 w-72 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg shadow-xl z-20 max-h-60 overflow-y-auto">
                  {filteredReviews.length === 0 ? <div className="px-3 py-3 text-center text-[10px] text-gray-400">No reviews found</div> :
                    filteredReviews.map(r => (
                      <button key={r.review_id} onClick={() => { selectReview(r.review_id); setShowReviewList(false); setSearchQuery(""); }}
                        className={`w-full text-left px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors ${r.review_id === selectedReviewId ? "bg-navy-50 dark:bg-navy-750" : ""}`}>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-semibold text-navy-900 dark:text-white truncate flex-1">{r.contract_name}</span>
                          <span className={`text-[8px] px-1 py-0.5 rounded-full font-medium ${
                            r.sla_status === "critical_overdue" ? "bg-red-100 text-red-700" : r.sla_status === "overdue" ? "bg-red-50 text-red-600" : r.sla_status === "warning" ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"
                          }`}>{r.sla_status.replace(/_/g, " ")}</span>
                        </div>
                        <div className="flex items-center gap-2 text-[8px] text-gray-500 mt-0.5">
                          <span>{r.vendor}</span><span>·</span><span>{r.document_type}</span>
                          {r.risk_score != null && <><span>·</span><span className={`font-semibold ${r.risk_score >= 8 ? "text-red-600" : r.risk_score >= 6 ? "text-orange-600" : "text-gray-500"}`}>{r.risk_score.toFixed(1)}</span></>}
                        </div>
                      </button>
                    ))}
                </div>
              </>
            )}
          </div>

          {/* Context indicator */}
          {selectedReview && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-gray-100 dark:bg-navy-700 text-[9px] text-gray-600 dark:text-gray-300">
              <FileText className="w-3 h-3" />
              {selectedReview.contract_number && (
                <span className="text-[10px] font-mono font-semibold text-navy-700 dark:text-navy-200">{selectedReview.contract_number}</span>
              )}
              {selectedReview.review_number && (
                <span className="text-[9px] font-mono text-gray-500 dark:text-gray-400">{selectedReview.review_number}</span>
              )}
              <button
                onClick={() => router.push(`/contracts/${selectedReview.review_id}`)}
                className="font-medium truncate max-w-[180px] hover:text-blue-600 hover:underline cursor-pointer text-left bg-transparent border-none"
                title={`${selectedReview.contract_number ? selectedReview.contract_number + ' — ' : ''}${selectedReview.contract_name}${selectedReview.original_filename ? ' (' + selectedReview.original_filename + ')' : ''}`}
              >
                {selectedReview.contract_name}
              </button>
              {selectedReview.original_filename && selectedReview.original_filename !== selectedReview.contract_name && (
                <span className="text-gray-400 truncate max-w-[100px]" title={selectedReview.original_filename}>
                  ({selectedReview.original_filename})
                </span>
              )}
              <span className="text-gray-400">·</span>
              <span>{selectedReview.vendor}</span>
              {criticalCount > 0 && (
                <span className="flex items-center gap-0.5 px-1 py-0.5 rounded bg-red-100 text-red-700 text-[8px] font-medium">
                  <AlertTriangle className="w-2 h-2" /> {criticalCount} critical
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* Panel toggles */}
          <button onClick={() => setShowLeftPanel(prev => !prev)}
            className={`p-1 rounded transition-colors ${showLeftPanel ? "bg-navy-100 text-navy-700 dark:bg-navy-700 dark:text-navy-200" : "text-gray-400 hover:bg-gray-100 dark:hover:bg-navy-700"}`} title="Toggle document (P)">
            <PanelLeft className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => setShowRightPanel(prev => !prev)}
            className={`p-1 rounded transition-colors ${showRightPanel ? "bg-navy-100 text-navy-700 dark:bg-navy-700 dark:text-navy-200" : "text-gray-400 hover:bg-gray-100 dark:hover:bg-navy-700"}`} title="Toggle context panel">
            <PanelRight className="w-3.5 h-3.5" />
          </button>
          <div className="w-px h-4 bg-gray-200 dark:bg-navy-700 mx-0.5" />

          {/* Quick Actions — approve/reject only while review is active */}
          {selectedReview && (
            <>
              {isReviewDecisionLocked(selectedReview, workflow) ? (
                <div className="flex items-center gap-1">
                  {([
                    { key: "status", value: selectedReview.status },
                    ...(workflow?.current_stage &&
                    workflow.current_stage !== selectedReview.status
                      ? [{ key: "stage", value: workflow.current_stage }]
                      : []),
                  ] as { key: string; value: string }[]).map(({ key, value }) => {
                    const Icon = value === "rejected" ? XCircle : CheckCircle2;
                    return (
                      <span
                        key={key}
                        className={`inline-flex items-center gap-1 px-1.5 py-1 text-[9px] font-semibold rounded ${reviewStatusBadgeClass(value)}`}
                      >
                        <Icon className="w-3 h-3" />
                        {formatReviewStatusLabel(value)}
                      </span>
                    );
                  })}
                </div>
              ) : (
                <>
                  <button
                    onClick={handleApprove}
                    disabled={approveMutation.isPending || hasBlockingFindings}
                    className="flex items-center gap-1 px-1.5 py-1 text-[9px] font-medium rounded hover:bg-green-50 text-green-700 transition-colors disabled:opacity-40"
                    title={
                      hasBlockingFindings
                        ? `${openFindingsData?.count ?? 0} critical/high finding(s) unresolved — resolve or dismiss them first`
                        : "Approve review"
                    }
                  >
                    {approveMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                    Approve
                  </button>
                  <button
                    onClick={openRejectModal}
                    disabled={approveMutation.isPending || rejectMutation.isPending}
                    className="flex items-center gap-1 px-1.5 py-1 text-[9px] font-medium rounded hover:bg-red-50 text-red-600 transition-colors disabled:opacity-40"
                    title="Reject review (reason required)"
                  >
                    {rejectMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
                    Reject
                  </button>
                  {approveError && (
                    <span className="text-[9px] text-red-600 max-w-[200px]" title={approveError}>
                      {approveError.length > 80 ? approveError.slice(0, 80) + "…" : approveError}
                    </span>
                  )}
                </>
              )}
              <ReviewMoreActionsMenu
                review={selectedReview}
                selectedFindingId={selectedFindingId}
                findings={findings}
                activeSection={activeSection}
                onLocateClause={(findingId) => {
                  setShowLeftPanel(true);
                  if (activeSection === "redline") {
                    return;
                  }
                  setSelectedFindingId(findingId);
                  setExpandedFindingId(findingId);
                  if (activeSection !== "recommendations") {
                    setActiveSection("findings");
                  }
                }}
                onNavigateSection={setActiveSection}
              />
            </>
          )}

          {/* Hotkey hint — subtle */}
          <div className="hidden xl:flex items-center gap-1 ml-1 px-1.5 py-1 rounded text-[8px] text-gray-400">
            <Zap className="w-2 h-2" /> S · 1-7 · V versions · N/P finding · ⌘P doc
          </div>
        </div>
      </div>

      {locateToast && (
        <div className="mx-4 mt-1 px-3 py-1.5 rounded-lg border border-navy-200 bg-navy-50 text-[10px] font-medium text-navy-800 dark:border-navy-600 dark:bg-navy-800 dark:text-navy-100 shadow-sm z-30">
          {locateToast}
        </div>
      )}

      {selectedReviewId && (
        <div className="mx-4 mt-2">
          <AnalysisPipelineBanner reviewId={selectedReviewId} />
        </div>
      )}

      {/* ── Reject modal (reason required → audit trail) ─────────────── */}
      <AnimatePresence>
        {showRejectModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4"
            onClick={closeRejectModal}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-4 shadow-xl dark:border-navy-700 dark:bg-navy-800"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-3 flex items-center gap-2">
                <XCircle className="h-5 w-5 text-red-600" />
                <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Reject Review</h3>
              </div>
              <p className="mb-3 text-[11px] text-gray-500 dark:text-gray-400">
                Provide a reason for rejection. This note is saved to the audit trail and visible under the Audit tab.
              </p>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                Rejection Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                value={rejectionReason}
                onChange={(e) => {
                  setRejectionReason(e.target.value);
                  setRejectError(null);
                }}
                rows={4}
                autoFocus
                placeholder="e.g., Unacceptable liability caps, missing indemnification clause, vendor refuses required security terms…"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-red-400 focus:outline-none focus:ring-1 focus:ring-red-200 dark:border-navy-600 dark:bg-navy-700 dark:text-gray-100"
              />
              {rejectError && (
                <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
                  {rejectError}
                </p>
              )}
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={closeRejectModal}
                  className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-navy-700"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleReject}
                  disabled={rejectMutation.isPending || !rejectionReason.trim()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {rejectMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Reject Review
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Section Tabs (compact) ────────────────────────────────────── */}
      <div className="flex items-center border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 px-2 flex-shrink-0">
        {sections.map(s => {
          const Icon = s.icon;
          const isActive = activeSection === s.id || (s.id === "redline" && activeSection === "findings" && false);
          const badge =
            s.id === "audit"
              ? (auditBadgeCount > 0 ? `(${auditBadgeCount})` : undefined)
              : activeBadges[s.id];
          return (
            <button key={s.id} onClick={() => setActiveSection(s.id as ReviewSection)}
              className={`flex items-center gap-1 px-2.5 py-2 text-[10px] font-medium border-b-2 transition-all ${
                activeSection === s.id
                  ? "border-navy-600 text-navy-700 dark:border-navy-300 dark:text-navy-200"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:hover:text-gray-300"
              }`}>
              <Icon className="w-3.5 h-3.5" />
              {s.label}
              {badge !== undefined && (
                <span className={`ml-0.5 text-[8px] font-bold px-1 py-0.5 rounded-full ${
                  activeSection === s.id ? "bg-navy-600 text-white dark:bg-navy-300 dark:text-navy-900" : "bg-gray-200 text-gray-600 dark:bg-navy-700 dark:text-gray-300"
                }`}>{badge}</span>
              )}
              <span className="text-[8px] text-gray-400 ml-0.5 hidden sm:inline">[{s.shortcut}]</span>
            </button>
          );
        })}
      </div>

      {/* ── Main 3-Panel Layout ────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── LEFT: Document Viewer (35%) ──────────────────────────────── */}
        <AnimatePresence mode="wait">
          {showLeftPanel && (
            <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: "35%", opacity: 1 }} exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.15 }} className="border-r border-gray-200 dark:border-navy-700 overflow-hidden flex-shrink-0"
              style={{ minWidth: showLeftPanel ? "340px" : "0px" }}>
              <DocumentViewer review={selectedReview} findings={findings} selectedFindingId={selectedFindingId}
                onFindingClick={(id) => { setSelectedFindingId(id); setExpandedFindingId(id); setActiveSection("findings"); }} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── CENTER: Findings Rail / Workspace (PRIMARY) ──────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white dark:bg-navy-800">
          {!selectedReviewId ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-sm">
                <Brain className="w-12 h-12 text-navy-200 dark:text-navy-600 mx-auto mb-3" />
                <h2 className="text-base font-semibold text-navy-900 dark:text-white mb-1">Select a Review</h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Search for a contract above to begin reviewing</p>
                <div className="grid grid-cols-2 gap-1.5 text-left text-[10px] text-gray-500">
                  {[
                    { key: "S/1-7", desc: "Sections" }, { key: "N", desc: "Next finding" },
                    { key: "P", desc: "Previous finding" }, { key: "V", desc: "Versions" },
                    { key: "⌘P", desc: "Toggle document" }, { key: "Esc", desc: "Clear selection" },
                  ].map(s => (
                    <div key={s.key} className="flex items-center gap-1.5 p-1.5 rounded bg-gray-50 dark:bg-navy-700">
                      <kbd className="px-1 py-0.5 rounded bg-white dark:bg-navy-600 border border-gray-200 text-[8px] font-mono font-bold">{s.key}</kbd>
                      <span>{s.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              {/* Overview = Summary + Explainability + Risk Reduction */}
              {(activeSection === "overview" || activeSection === "summary" || activeSection === "explainability" || activeSection === "risk_reduction") && (
                <div className="divide-y divide-gray-100 dark:divide-navy-700">
                  <ReviewSummarySection />
                  <RiskReductionSection />
                  <ExplainabilitySection />
                </div>
              )}
              {/* Findings */}
              {activeSection === "findings" && <FindingsSection />}
              {/* Redlines */}
              {activeSection === "redline" && <RedlineWorkspace />}
              {/* Policy */}
              {activeSection === "policy" && <PolicyIssuesSection />}
              {/* Recommendations */}
              {activeSection === "recommendations" && <RecommendationsSection />}
              {/* Workflow — standalone tab */}
              {activeSection === "workflow" && <WorkflowSection />}
              {/* Audit */}
              {activeSection === "audit" && <AuditTrailSection />}
              {/* Versions */}
              {activeSection === "versions" && <VersionsSection />}
              {activeSection === "obligations" && <ObligationsSection />}
            </div>
          )}
        </div>

        {/* ── RIGHT: Compact Metadata + Workflow (25%) ─────────────────── */}
        <AnimatePresence mode="wait">
          {showRightPanel && selectedReviewId && (
            <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: "25%", opacity: 1 }} exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.15 }} className="border-l border-gray-200 dark:border-navy-700 overflow-y-auto flex-shrink-0 bg-white dark:bg-navy-800"
              style={{ minWidth: showRightPanel ? "260px" : "0px" }}>
              <CompactContextPanel />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ── Compact Context Panel (dense, collapsible, insight-rich) ────────────────

function CompactContextPanel() {
  const ctx = useReviewContext();
  const { selectedReview, workflow, findings, recommendations, policyViolations, setActiveSection } = ctx;

  const [expandedSection, setExpandedSection] = useState<string | null>("risk");

  if (!selectedReview) return null;

  const openFindings = findings.filter(f => f.status === "open");
  const criticalFindings = findings.filter(f => f.severity === "critical" && f.status === "open");
  const pendingRecs = recommendations?.filter(r => r.status === "pending") ?? [];
  const openViolations = policyViolations?.filter(v => v.status === "open") ?? [];

  const Section = ({ id, label, children, badge, onClick }: { id: string; label: string; children: React.ReactNode; badge?: string | number; onClick?: () => void }) => {
    const isOpen = expandedSection === id;
    return (
      <div className="border-b border-gray-100 dark:border-navy-700">
        <button onClick={() => { if (onClick) onClick(); setExpandedSection(isOpen ? null : id); }}
          className="w-full flex items-center justify-between px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors">
          <span className="text-[8px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">{label}</span>
          <div className="flex items-center gap-1">
            {badge !== undefined && (
              <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full bg-navy-100 text-navy-700 dark:bg-navy-700 dark:text-navy-200">{badge}</span>
            )}
            {isOpen ? <ChevronUp className="w-2.5 h-2.5 text-gray-400" /> : <ChevronDown className="w-2.5 h-2.5 text-gray-400" />}
          </div>
        </button>
        {isOpen && <div className="px-3 pb-2">{children}</div>}
      </div>
    );
  };

  return (
    <div className="divide-y divide-gray-100 dark:divide-navy-700 text-[10px]">
      {/* Risk Score — compact bar */}
      <Section id="risk" label="Risk Assessment" badge={selectedReview.risk_score?.toFixed(1)}>
        <div className="h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden mb-1.5">
          <div className={`h-full rounded-full ${
            (selectedReview.risk_score ?? 0) >= 8 ? "bg-red-500" :
            (selectedReview.risk_score ?? 0) >= 6 ? "bg-orange-500" :
            (selectedReview.risk_score ?? 0) >= 4 ? "bg-amber-500" : "bg-green-500"
          }`} style={{ width: `${((selectedReview.risk_score ?? 0) / 10) * 100}%` }} />
        </div>
        <div className="flex items-center justify-between mb-1 text-[8px]">
          <span className="text-gray-400">Risk Trend</span>
          <span className={`flex items-center gap-0.5 font-medium ${
            (selectedReview.risk_score ?? 0) >= 7 ? "text-red-600" :
            (selectedReview.risk_score ?? 0) >= 5 ? "text-amber-600" : "text-green-600"
          }`}>
            {(selectedReview.risk_score ?? 0) >= 7 ? <TrendingUp className="w-2.5 h-2.5" /> :
             (selectedReview.risk_score ?? 0) >= 5 ? <Minus className="w-2.5 h-2.5" /> :
             <TrendingDown className="w-2.5 h-2.5" />}
            {(selectedReview.risk_score ?? 0) >= 7 ? "Elevated" :
             (selectedReview.risk_score ?? 0) >= 5 ? "Moderate" : "Low"}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-1 text-[8px]">
          <div className="text-center p-1 rounded bg-red-50 dark:bg-red-900/10">
            <span className="font-bold text-red-600">{criticalFindings.length}</span>
            <span className="text-gray-500 ml-0.5">critical</span>
          </div>
          <div className="text-center p-1 rounded bg-amber-50 dark:bg-amber-900/10">
            <span className="font-bold text-amber-600">{openFindings.length}</span>
            <span className="text-gray-500 ml-0.5">open</span>
          </div>
          <div className="text-center p-1 rounded bg-blue-50 dark:bg-blue-900/10">
            <span className="font-bold text-blue-600">{Math.round((selectedReview.risk_score ?? 0) * 10)}%</span>
            <span className="text-gray-500 ml-0.5">conf</span>
          </div>
        </div>
      </Section>

      {/* Contract Details — compact */}
      <Section id="details" label="Contract Details">
        <div className="space-y-0.5 text-[9px]">
          <div className="flex justify-between"><span className="text-gray-400">Vendor</span><span className="font-medium text-navy-900 dark:text-white truncate ml-2 max-w-[140px]">{selectedReview.vendor}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">Type</span><span>{selectedReview.document_type}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">Status</span><span className={`font-medium capitalize ${
            selectedReview.status === "approved" ? "text-green-600" : selectedReview.status === "escalated" ? "text-red-600" : ""
          }`}>{selectedReview.status.replace(/_/g, " ")}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">Priority</span><span className={`font-medium capitalize ${
            selectedReview.priority === "critical" ? "text-red-600" : selectedReview.priority === "high" ? "text-orange-600" : ""
          }`}>{selectedReview.priority}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">Assignee</span><span className="font-medium">{selectedReview.assigned_to_name || "—"}</span></div>
        </div>
      </Section>

      {/* SLA & Queue Position */}
      <Section id="sla" label="SLA & Queue" badge={selectedReview.sla_status.replace(/_/g, " ")}>
        <div className={`px-2 py-1 rounded text-[9px] font-medium mb-1.5 ${
          selectedReview.sla_status === "critical_overdue" ? "bg-red-100 text-red-700" :
          selectedReview.sla_status === "overdue" ? "bg-red-50 text-red-600" :
          selectedReview.sla_status === "warning" ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"
        }`}>
          <div className="flex items-center justify-between">
            <span>{selectedReview.overdue_hours > 0 ? `${selectedReview.overdue_hours}h overdue` : `${Math.round((selectedReview.risk_score ?? 0) * 10)}h remaining`}</span>
            {workflow && <span>#{workflow.queue_position} of {workflow.queue_total}</span>}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-1 text-[8px]">
          <div className="text-gray-500">Age: <span className={`font-medium ${selectedReview.age_hours > 72 ? "text-red-600" : selectedReview.age_hours > 48 ? "text-amber-600" : ""}`}>{Math.round(selectedReview.age_hours)}h</span></div>
          <div className="text-gray-500">Escalation: <span className={`font-medium ${selectedReview.escalation_level > 0 ? "text-red-600" : ""}`}>{selectedReview.escalation_level > 0 ? `L${selectedReview.escalation_level}` : "None"}</span></div>
        </div>
      </Section>

      {/* Workflow Stage Dots */}
      {workflow && (
        <Section id="workflow" label="Workflow" badge={workflow.current_stage.replace(/_/g, " ")}>
          <div className="flex items-center gap-0.5 mb-1.5">
            {workflow.stages.slice(0, 7).map((stage, i) => (
              <React.Fragment key={stage.id}>
                <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                  stage.status === "completed" ? "bg-green-400" :
                  stage.status === "current" ? "bg-blue-500 ring-1 ring-blue-300" :
                  stage.status === "rejected" ? "bg-red-400" : "bg-gray-200 dark:bg-navy-700"
                }`} title={stage.label}>
                  {(stage.status === "completed" || stage.status === "current") && (
                    <span className="text-[6px] font-bold text-white">{i + 1}</span>
                  )}
                </div>
                {i < workflow.stages.length - 1 && i < 6 && (
                  <div className={`flex-1 h-px ${stage.status === "completed" ? "bg-green-400" : "bg-gray-200 dark:bg-navy-700"}`} />
                )}
              </React.Fragment>
            ))}
          </div>
          {workflow.reviewers.length > 0 && (
            <div className="flex items-center gap-1 mt-1">
              {workflow.reviewers.map(r => (
                <div key={r.user_id} className="group relative">
                  <div className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center text-[7px] font-bold text-navy-600 cursor-default">
                    {r.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                  </div>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-gray-900 text-white text-[7px] px-1.5 py-0.5 rounded whitespace-nowrap z-10">
                    {r.name} · {r.role} · {r.workload_pct}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* Findings Summary — clickable to jump to Findings tab */}
      <Section id="findings-summary" label="Findings" badge={findings.length} onClick={() => setActiveSection("findings")}>
        <div className="space-y-0.5 text-[9px]">
          <div className="flex justify-between"><span className="text-gray-400">Critical</span><span className="font-medium text-red-600">{findings.filter(f => f.severity === "critical").length}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">High</span><span className="font-medium text-orange-600">{findings.filter(f => f.severity === "high").length}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">Medium</span><span className="font-medium text-amber-600">{findings.filter(f => f.severity === "medium").length}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">Open</span><span className="font-medium">{openFindings.length}</span></div>
          <div className="flex justify-between"><span className="text-gray-400">Resolved</span><span className="font-medium text-green-600">{findings.filter(f => f.status === "resolved" || f.status === "dismissed").length}</span></div>
        </div>
      </Section>

      {/* Policy Violations — clickable to jump to Policy tab */}
      {openViolations.length > 0 && (
        <Section id="violations" label="Policy Violations" badge={openViolations.length} onClick={() => setActiveSection("policy")}>
          <div className="space-y-1">
            {openViolations.slice(0, 3).map(v => (
              <div key={v.id} className="flex items-start gap-1 text-[8px]">
                <AlertTriangle className="w-2.5 h-2.5 text-red-400 mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-gray-700 dark:text-gray-300 truncate">{v.policy_name}</p>
                  <p className="text-gray-400">{v.clause_type}</p>
                </div>
              </div>
            ))}
            {openViolations.length > 3 && <p className="text-[8px] text-gray-400">+{openViolations.length - 3} more</p>}
          </div>
        </Section>
      )}

      {/* Recommendations — clickable to jump to Recs tab */}
      {pendingRecs.length > 0 && (
        <Section id="recs" label="Recommendations" badge={pendingRecs.length} onClick={() => setActiveSection("recommendations")}>
          <div className="space-y-1">
            {pendingRecs.slice(0, 3).map(r => (
              <div key={r.recommendation_id} className="flex items-start gap-1 text-[8px]">
                <Lightbulb className="w-2.5 h-2.5 text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-gray-700 dark:text-gray-300 truncate">{r.title}</p>
                  <p className="text-gray-400">{r.impact} impact · {r.effort} effort</p>
                </div>
              </div>
            ))}
            {pendingRecs.length > 3 && <p className="text-[8px] text-gray-400">+{pendingRecs.length - 3} more</p>}
          </div>
        </Section>
      )}
    </div>
  );
}

// ── Exported Platform ───────────────────────────────────────────────────────

interface EnterpriseReviewPlatformProps {
  preselectedReviewId?: string;
  preselectedContractId?: string;
  /** Optional initial section to land on (e.g. "redline" from a deep link). */
  initialSection?: ReviewSection;
}

export function EnterpriseReviewPlatform({ preselectedReviewId, preselectedContractId, initialSection }: EnterpriseReviewPlatformProps) {
  return (
    <ReviewContextProvider
      preselectedReviewId={preselectedReviewId}
      preselectedContractId={preselectedContractId}
      initialSection={initialSection}
    >
      <EnterpriseReviewPlatformInner />
    </ReviewContextProvider>
  );
}

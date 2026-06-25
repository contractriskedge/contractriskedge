/**
 * ContractDetailWorkspace — Repository-centric contract detail view.
 *
 * Purpose: Contract lifecycle overview, metadata, obligations, version history,
 * high-level risk summary, contract intelligence, and document preview.
 *
 * This is a REPOSITORY view — NOT a review/redline workspace.
 * For detailed review operations, use the dedicated workspaces:
 *   - /reviews/ai-workspace  (AI Review Workspace)
 *   - /reviews/{id}/redline   (Redline Experience)
 *
 * KEEP:
 * - Contract text preview
 * - Risk overview & exposure summary
 * - AI summary
 * - Lifecycle metadata
 * - Obligations
 * - Version history
 * - Document relationships
 * - Activity timeline
 *
 * REMOVED (delegated to dedicated workspaces):
 * - Detailed findings execution → "Open AI Review Workspace"
 * - Detailed explainability → "Open AI Review Workspace"
 * - Mitigation execution → "Open Redline Session"
 * - Inline review operations → "Open AI Review Workspace"
 * - Redline editing → "Open Redline Session"
 * - Negotiation editing → "Start Negotiation"
 * - Reviewer operational workflow controls → "Open AI Review Workspace"
 */

"use client";

import React, { useState, useMemo } from "react";
import { useRouter, notFound } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, FileText, Brain, Shield, AlertTriangle, CheckCircle2,
  Clock, User, RefreshCw, Download, Share2, ExternalLink,
  Edit3, GitCompare, MessageSquare, Activity, Calendar,
  Building2, Globe, Loader2, ChevronDown, ChevronRight, ChevronUp,
  BarChart3, BookOpen, XCircle, DollarSign, GitBranch, Lock, Archive,
  Tag, ListChecks, FileSignature,
} from "lucide-react";
import {
  useContractDetail,
  useContractActivity,
  useContractObligations,
  useContractVersions,
  useContractFindings,
  useContractClauses,
  useContractWorkflowHistory,
  useContractObligationActivity,
  useContractSignatures,
} from "./hooks";
import { useRiskBreakdown } from "@/services/hooks";
import { reviewService } from "@/services/api/reviews";
import { api } from "@/services";
import { useCloseReview } from "@/services/hooks/useReviews";
import type { GovernanceTraceability } from "@/services/api/client";
import { RelatedReviewsPanel } from "./RelatedReviewsPanel";
import { LifecycleHistoryPanel } from "./LifecycleHistoryPanel";
import { WorkflowTimelinePanel, type TimelineEvent } from "./WorkflowTimelinePanel";
import { AuditTrailPanel } from "./AuditTrailPanel";
import { IntelligenceHub } from "./IntelligenceHub";
import { formatDate } from "@/lib/date-utils";
import { ApprovalModal } from "@/components/review/ApprovalModal";
import { CollapsibleSection } from "@/components/shared/CollapsibleSection";

// ── Props ───────────────────────────────────────────────────────────────────

interface ContractDetailWorkspaceProps {
  contractId: string;
}

// ── Main Component ──────────────────────────────────────────────────────────

export function ContractDetailWorkspace({ contractId }: ContractDetailWorkspaceProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"overview" | "insights" | "clauses" | "activity" | "versions" | "reviews" | "lifecycle" | "workflow" | "signatures">("overview");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [closeModalOpen, setCloseModalOpen] = useState(false);
  const [closeReason, setCloseReason] = useState("");

  // ── Action Mutations ──────────────────────────────────────────
  const approveMut = useMutation({
    mutationFn: ({ decision, comment, conditions }: { decision: string; comment: string; conditions?: Record<string, unknown> }) =>
      reviewService.approve(contractId, { decision, comments: comment, conditions }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["contract-detail"] }); setActionLoading(null); setApprovalModalOpen(false); },
    onError: () => setActionLoading(null),
  });
  const rejectMut = useMutation({
    mutationFn: ({ comment, category, severity }: { comment: string; category: string; severity: string }) =>
      reviewService.approve(contractId, { decision: "rejected", comments: comment, conditions: { category, severity } }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["contract-detail"] }); setActionLoading(null); setApprovalModalOpen(false); },
    onError: () => setActionLoading(null),
  });
  const finalizeMut = useMutation({
    mutationFn: () => reviewService.finalize(contractId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["contract-detail"] }); setActionLoading(null); },
    onError: () => setActionLoading(null),
  });
  const closeMut = useCloseReview();
  const handleClose = async () => {
    if (closeReason.trim().length < 5) return;
    setActionLoading("close");
    try {
      await closeMut.mutateAsync({ reviewId: contractId, reason: closeReason.trim() });
      setCloseModalOpen(false);
      setCloseReason("");
      queryClient.invalidateQueries({ queryKey: ["contract-detail"] });
    } catch {
      // Error handled by mutation state
    }
    setActionLoading(null);
  };

  // ── Data Fetching (repository-only) ──────────────────────────────────

  const { data: contract, isLoading: contractLoading, error: contractError, refetch } = useContractDetail(contractId);
  const { data: activityData } = useContractActivity(contractId);
  const { data: obligationsData } = useContractObligations(contractId);
  const { data: obligationActivityData } = useContractObligationActivity(contractId);
  const { data: versionsData } = useContractVersions(contractId);
  const { data: findingsData } = useContractFindings(contractId);
  const { data: clausesData } = useContractClauses(contractId);
  const { data: workflowHistoryData } = useContractWorkflowHistory(contractId);
  const { data: signaturesData } = useContractSignatures(contractId);

  const activityEvents = useMemo(() => {
    const contractEvents = activityData?.events ?? [];
    const obligationEvents = obligationActivityData?.obligationEvents ?? [];
    // Merge and sort newest first
    return [...contractEvents, ...obligationEvents].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [activityData, obligationActivityData]);
  const obligations = obligationsData?.obligations ?? [];
  const versions = versionsData?.versions ?? [];
  const findings = findingsData?.findings ?? [];
  const clauses = clausesData?.clauses ?? [];
  const workflowEvents = workflowHistoryData?.events ?? [];

  // Map the backend timeline event shape into the TimelineEvent shape
  // used by WorkflowTimelinePanel. The backend already provides a
  // normalised audit-grade view; we just translate type strings.
  const workflowTimeline: TimelineEvent[] = useMemo(() => {
    return (workflowEvents ?? []).map((e) => {
      const rawType = String(e.type ?? "stage_changed");
      const type: TimelineEvent["type"] =
        rawType === "approved" || rawType === "conditionally_approved" ? "approved" :
        rawType === "rejected" ? "rejected" :
        rawType === "escalated" ? "escalated" :
        rawType === "assigned" ? "assigned" :
        rawType === "ai_analyzed" || rawType === "ai_analysis_completed" ? "ai_analyzed" :
        rawType === "completed" || rawType === "executed" ? "completed" :
        "stage_changed";
      return {
        id: String(e.id ?? `${rawType}-${e.timestamp}-${e.actor}`),
        type,
        timestamp: String(e.timestamp ?? new Date().toISOString()),
        actor: String(e.actor ?? "system"),
        actorRole: e.role ? String(e.role) : undefined,
        fromValue: e.previous_value ? String(e.previous_value) : undefined,
        toValue: e.new_value ? String(e.new_value) : undefined,
        reason: e.reason ? String(e.reason) : undefined,
      };
    });
  }, [workflowEvents]);

  // ── Navigation Actions ───────────────────────────────────────────────
  // Routes that are known to exist:
  //   /reviews/ai-workspace?contractId=…   (AI Review workspace)
  //   /negotiation                          (Negotiation index — the
  //                                          per-contract deep-link
  //                                          /negotiation/{id} is not
  //                                          routed yet, so we keep the
  //                                          contract id available via
  //                                          query string instead.)
  const openAiReview = () => router.push(`/reviews/ai-workspace?contractId=${contractId}`);
  const openRedline = () => router.push(`/reviews/ai-workspace?contractId=${contractId}&tab=redline`);
  const openNegotiation = () => router.push(`/negotiation?contractId=${contractId}`);

  // Download the contract document via the API and trigger a browser
  // "save as" dialog. Falls back to opening in a new tab if the backend
  // doesn't expose a download URL.
  const handleDownload = async () => {
    if (!contract) return;
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}/contracts/${contractId}/document`,
        { credentials: "include" },
      );
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = contract.filename || `${contract.name}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        return;
      }
    } catch {
      // fall through to the no-API fallback
    }
    // Fallback: open the workspace document URL in a new tab.
    if (contract.document_url) {
      window.open(contract.document_url, "_blank", "noopener,noreferrer");
    }
  };

  // Copy a shareable deep-link to this contract to the clipboard. The
  // toast/feedback is intentionally simple (the page header is small and
  // we don't want a third-party toast library just for this).
  const [shareCopied, setShareCopied] = useState(false);
  const handleShare = async () => {
    if (typeof window === "undefined") return;
    const url = `${window.location.origin}/contracts/${contractId}`;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        // Fallback for non-secure contexts
        const ta = document.createElement("textarea");
        ta.value = url;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
      }
      setShareCopied(true);
      window.setTimeout(() => setShareCopied(false), 2000);
    } catch {
      // Silent failure — the share button is best-effort.
    }
  };

  // ── Loading ──────────────────────────────────────────────────────────

  if (contractLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-navy-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading contract details...</p>
        </div>
      </div>
    );
  }

  if (contractError || !contract) {
    // If the server actually returned a 404 for this contract id, hand off
    // to the route-level not-found page so the user sees a proper 404
    // screen. Otherwise, fall back to a generic error state.
    const apiErr = contractError as { status_code?: number; status?: number; message?: string } | null;
    const status = apiErr?.status_code ?? apiErr?.status
      ?? (apiErr?.message?.includes("not found") ? 404 : undefined);
    if (status === 404) {
      notFound();
    }
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-navy-900">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">Failed to load contract</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Contract {contractId} could not be found or accessed.</p>
          <button onClick={() => router.push("/contracts")} className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Contracts
          </button>
        </div>
      </div>
    );
  }

  const openObligations = obligationsData?.open ?? obligations.filter(
    o => !["completed", "closed", "waived", "cancelled", "archived"].includes(o.status)
  ).length;
  const openCriticalFindings = findings.filter(f => (f.severity === "critical" || f.severity === "high") && f.status === "open").length;

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900">
      {/* ── Sticky Action Bar ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 shadow-sm z-10">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/contracts")} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors" aria-label="Back">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-navy-600 dark:text-navy-300" />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-navy-900 dark:text-white leading-tight">{contract.name}</h1>
                {/* Lifecycle Status Badge */}
                <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${
                  contract.status === "active" || contract.status === "executed" ? "bg-green-100 text-green-700" :
                  contract.status === "expiring_soon" ? "bg-yellow-100 text-yellow-700" :
                  contract.status === "expired" || contract.status === "critical_overdue" ? "bg-red-100 text-red-700" :
                  contract.status === "archived" || contract.status === "closed" ? "bg-gray-100 text-gray-600" :
                  contract.status === "approved" || contract.status === "finalized" ? "bg-blue-100 text-blue-700" :
                  contract.status === "draft" || contract.status === "ai_analyzed" ? "bg-gray-100 text-gray-500" :
                  "bg-gray-100 text-gray-600"
                }`}>
                  {contract.status === "expiring_soon" ? "Expiring" :
                   contract.status === "critical_overdue" ? "Expired" :
                   contract.status.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">
                {contract.contract_number ? `${contract.contract_number} · ` : ""}
                {contract.filename} · {contract.total_pages} pages · v{versions.length > 0 ? versions[0].version_number : 1}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <button onClick={openAiReview} className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700 transition-colors shadow-sm">
            <Brain className="w-3.5 h-3.5" /> AI Review
          </button>
          <button onClick={openRedline} className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-600 transition-colors">
            <Edit3 className="w-3.5 h-3.5" /> Redline
          </button>
          <button onClick={openNegotiation} className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-600 transition-colors">
            <GitCompare className="w-3.5 h-3.5" /> Negotiate
          </button>
          <div className="w-px h-5 bg-gray-200 dark:bg-navy-700 mx-1" />
          {/* Approve / Reject / Finalize actions — only show when review status allows */}
          {contract.status && ["in_review", "legal_review", "security_review", "procurement_review", "negotiation", "escalated", "exec_approval"].includes(contract.status) && (
            <>
              <button
                onClick={() => { setActionLoading("approve"); setApprovalModalOpen(true); }}
                disabled={actionLoading === "approve" || approveMut.isPending}
                className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition-colors shadow-sm"
                title="Approve review"
              >
                {approveMut.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                Approve
              </button>
              <button
                onClick={() => { setActionLoading("reject"); setApprovalModalOpen(true); }}
                disabled={actionLoading === "reject" || rejectMut.isPending}
                className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
                title="Reject review"
              >
                {rejectMut.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />}
                Reject
              </button>
            </>
          )}
          {contract.status === "approved" && (
            <button
              onClick={() => { setActionLoading("finalize"); finalizeMut.mutate(); }}
              disabled={actionLoading === "finalize" || finalizeMut.isPending}
              className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50 transition-colors shadow-sm"
              title="Finalize approved review"
            >
              {finalizeMut.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
              Finalize
            </button>
          )}
          {/* Send for Signature — for finalized or approved contracts */}
          {(contract.status === "finalized" || contract.status === "approved" || contract.status === "active") && (
            <button
              onClick={async () => {
                setActionLoading("sign");
                try {
                  // Step 1: Create signature request in draft status
                  const created: any = await api.post("/signatures", {
                    contract_id: contractId,
                    title: `Sign: ${contract.name || contract.filename || contractId}`,
                    provider: "docusign",
                    signers: [
                      {
                        email: "signer@contractriskedge.com",
                        name: "Contract Signer",
                        role: "signer",
                        signing_order: 1,
                      },
                    ],
                    email_subject: `Please sign: ${contract.name || contract.filename || "Contract"}`,
                    email_message: "This document is ready for your electronic signature via DocuSign.",
                  });
                  const requestId = created.id;
                  console.log("Signature request created:", requestId);

                  // Step 2: Prepare it (moves to 'preparing' status)
                  await api.post(`/signatures/${requestId}/prepare`);

                  // Step 3: Send it to DocuSign (creates envelope, sends email)
                  const sent: any = await api.post(`/signatures/${requestId}/send`, {
                    email_subject: `Please sign: ${contract.name || contract.filename || "Contract"}`,
                    email_message: "This document is ready for your electronic signature via DocuSign.",
                  });
                  console.log("Sent to DocuSign:", sent);
                  alert(`Envelope sent to DocuSign! Envelope ID: ${sent.provider_reference || "N/A"}. The signer will receive an email.`);
                  refetch();
                } catch (err: any) {
                  console.error("Failed to send for signature:", err);
                  alert(`Failed: ${err?.message || "Unknown error"}. Check console for details.`);
                } finally {
                  setActionLoading(null);
                }
              }}
              disabled={actionLoading === "sign"}
              className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-colors shadow-sm"
              title="Send for signature via DocuSign"
            >
              {actionLoading === "sign" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSignature className="w-3.5 h-3.5" />}
              Send for Signature
            </button>
          )}
          {/* Close — for finalized or executed contracts */}
          {(contract.status === "finalized" || contract.status === "executed") && (
            <button
              onClick={() => { setCloseModalOpen(true); setCloseReason(""); }}
              disabled={actionLoading === "close" || closeMut.isPending}
              className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
              title="Close contract — ends the lifecycle"
            >
              {closeMut.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Archive className="w-3.5 h-3.5" />}
              Close
            </button>
          )}
          {approveMut.isError && (
            <span className="text-[9px] text-red-600 max-w-[180px]" title={approveMut.error instanceof Error ? approveMut.error.message : "Error"}>
              {(approveMut.error instanceof Error ? approveMut.error.message : "Action failed").slice(0, 60)}…
            </span>
          )}
          {rejectMut.isError && (
            <span className="text-[9px] text-red-600 max-w-[180px]" title={rejectMut.error instanceof Error ? rejectMut.error.message : "Error"}>
              {(rejectMut.error instanceof Error ? rejectMut.error.message : "Action failed").slice(0, 60)}…
            </span>
          )}
          {finalizeMut.isError && (
            <span className="text-[9px] text-red-600 max-w-[180px]" title={finalizeMut.error instanceof Error ? finalizeMut.error.message : "Error"}>
              {(finalizeMut.error instanceof Error ? finalizeMut.error.message : "Action failed").slice(0, 60)}…
            </span>
          )}
          <div className="w-px h-5 bg-gray-200 dark:bg-navy-700 mx-1" />
          <button
            onClick={handleDownload}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 transition-colors"
            aria-label="Download contract"
            title="Download contract"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={handleShare}
            className={`relative p-1.5 rounded-lg transition-colors ${
              shareCopied
                ? "text-green-600 bg-green-50 dark:bg-green-900/20"
                : "text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700"
            }`}
            aria-label="Copy share link"
            title={shareCopied ? "Link copied!" : "Copy share link"}
          >
            <Share2 className="w-4 h-4" />
            {shareCopied && (
              <span className="absolute -bottom-7 right-0 whitespace-nowrap rounded bg-gray-900 text-white text-[10px] font-medium px-2 py-0.5 shadow-lg">
                Copied!
              </span>
            )}
          </button>
        </div>
      </div>

      {/* ── Main 2-Panel Layout ────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── LEFT: Document Preview ───────────────────────────────────── */}
        <div className="w-[45%] min-w-[360px] border-r border-gray-200 dark:border-navy-700 overflow-y-auto bg-white dark:bg-navy-800">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-400" />
                <span className="text-xs font-medium text-navy-900 dark:text-white">{contract.name}</span>
              </div>
              <p className="text-[10px] text-gray-400">{(contract.contract_type || "—")} · Page 1 of {contract.total_pages}</p>
            </div>

            <div className="bg-gray-50 dark:bg-navy-900 border border-gray-200 dark:border-navy-700 rounded-lg p-4 min-h-[400px]">
              <div className="text-[11px] leading-relaxed text-gray-700 dark:text-gray-300 space-y-2">
                <p className="font-semibold text-navy-900 dark:text-white text-xs">{contract.name}</p>
                <p className="text-gray-400 text-[10px]">Between {contract.vendor || "—"} and {contract.counterparty || "—"} · Effective: {formatDate(contract.effective_date)}</p>
                <hr className="border-gray-100 dark:border-navy-700 my-2" />
                <p><span className="font-medium">1.1 Services.</span> Vendor shall provide the services described in Exhibit A in accordance with the terms of this Agreement.</p>
                <p><span className="font-medium">1.2 Term.</span> This Agreement shall commence on the Effective Date and continue for an initial term of twelve (12) months.</p>
                <p className="text-gray-400 text-[10px] italic mt-4">Full document preview available in AI Review Workspace.</p>
              </div>
            </div>

            {/* AI Summary */}
            <div className="mt-3 p-3 rounded-lg bg-navy-50 dark:bg-navy-850 border border-navy-100 dark:border-navy-700">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Brain className="w-3.5 h-3.5 text-navy-600" />
                <span className="text-[10px] font-semibold text-navy-700 dark:text-navy-200 uppercase tracking-wider">AI Summary</span>
              </div>
              <p className="text-[11px] text-gray-700 dark:text-gray-300 leading-relaxed">
                {contract.ai_summary || "AI analysis pending. The contract has been queued for processing."}
              </p>
              {/* Quick links */}
              <div className="flex items-center gap-2 mt-2 pt-2 border-t border-navy-200/50 dark:border-navy-700/50">
                <button
                  onClick={openAiReview}
                  className="inline-flex items-center gap-1 text-[9px] font-medium text-navy-700 dark:text-navy-300 hover:text-navy-900 dark:hover:text-white transition-colors"
                >
                  <Brain className="w-3 h-3" /> Open Review Workspace
                </button>
                {(findings?.length ?? 0) > 0 && (
                  <button
                    onClick={() => setActiveTab("insights")}
                    className="inline-flex items-center gap-1 text-[9px] font-medium text-amber-700 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-100 transition-colors"
                  >
                    <FileText className="w-3 h-3" /> View Findings ({findings.length})
                  </button>
                )}
                {(findings?.length ?? 0) > 0 && (
                  <button
                    onClick={openRedline}
                    className="inline-flex items-center gap-1 text-[9px] font-medium text-rose-700 dark:text-rose-300 hover:text-rose-900 dark:hover:text-rose-100 transition-colors"
                  >
                    <Edit3 className="w-3 h-3" /> View Redlines
                  </button>
                )}
              </div>
            </div>

            {(contract.missing_clauses?.length ?? 0) > 0 && (
              <div className="mt-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <XCircle className="w-3.5 h-3.5 text-red-500" />
                  <span className="text-[10px] font-semibold text-red-700 dark:text-red-300 uppercase tracking-wider">Missing Clauses</span>
                </div>
                <div className="space-y-1">
                  {contract.missing_clauses.map(mc => (
                    <div key={mc} className="flex items-center gap-1.5 text-[10px] text-red-600 dark:text-red-400">
                      <AlertTriangle className="w-3 h-3 flex-shrink-0" /> {mc}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT: Repository Overview ───────────────────────────────── */}
        <div className="flex-1 overflow-y-auto bg-white dark:bg-navy-800">
          <div className="flex items-center border-b border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-900 px-2 overflow-x-auto">
            {[
              { id: "overview" as const, label: "Overview", icon: FileText },
              { id: "insights" as const, label: "AI Insights", icon: Brain, badge: findings.length },
              { id: "clauses" as const, label: "Clauses", icon: BookOpen, badge: clauses.length },
              { id: "workflow" as const, label: "Workflow", icon: GitBranch, badge: workflowTimeline.length },
              { id: "reviews" as const, label: "Related Reviews", icon: GitBranch },
              { id: "lifecycle" as const, label: "Lifecycle", icon: Clock },
              { id: "activity" as const, label: "Activity", icon: Activity, badge: activityEvents.length },
              { id: "versions" as const, label: "Versions", icon: Clock, badge: versions.length },
              { id: "signatures" as const, label: "Signatures", icon: FileSignature, badge: signaturesData?.length },
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-2.5 text-[11px] font-medium border-b-2 transition-all ${
                    isActive ? "border-navy-600 text-navy-700 dark:border-navy-300 dark:text-navy-200" : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:hover:text-gray-300"
                  }`}>
                  <Icon className="w-3.5 h-3.5" />{tab.label}
                  {tab.badge !== undefined && tab.badge > 0 && (
                    <span className={`ml-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full ${isActive ? "bg-navy-600 text-white" : "bg-gray-200 text-gray-600"}`}>{tab.badge}</span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="p-4">
            {activeTab === "overview" && (
              <div className="space-y-4">
                {/* Risk Overview */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-gradient-to-br from-white to-gray-50 dark:from-navy-800 dark:to-navy-850">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-semibold text-gray-500 uppercase">Risk Score</span>
                      <span className={`text-lg font-bold ${contract.risk_score >= 8 ? "text-red-600" : contract.risk_score >= 6 ? "text-orange-600" : contract.risk_score >= 4 ? "text-amber-600" : "text-green-600"}`}>{contract.risk_score}</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${contract.risk_score >= 8 ? "bg-red-500" : contract.risk_score >= 6 ? "bg-orange-500" : contract.risk_score >= 4 ? "bg-amber-500" : "bg-green-500"}`} style={{ width: `${(contract.risk_score / 10) * 100}%` }} />
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 text-[8px] text-gray-500">
                      <span className="capitalize font-medium">{contract.risk_level} risk</span>
                      <span>·</span>
                      <span>{Math.round(contract.confidence_score * 100)}% AI confidence</span>
                    </div>
                  </div>
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3">
                    <div className="text-[9px] font-semibold text-gray-500 uppercase mb-1">AI Findings</div>
                    <div className="text-lg font-bold text-navy-900 dark:text-white">{contract.ai_findings_count || 0}</div>
                    <div className="text-[8px] text-gray-500 mt-0.5">{contract.unresolved_risks || 0} unresolved risks</div>
                  </div>
                  <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3">
                    <div className="text-[9px] font-semibold text-gray-500 uppercase mb-1">Obligations</div>
                    <div className="text-lg font-bold text-navy-900 dark:text-white">{obligationsData?.total ?? obligations.length}</div>
                    <div className="flex items-center gap-2 mt-1 text-[8px]">
                      <span className="text-green-600 font-medium">{obligationsData?.completed ?? 0} completed</span>
                      <span className="text-gray-300">·</span>
                      <span className="text-amber-600 font-medium">{obligationsData?.open ?? openObligations} open</span>
                      {(obligationsData?.overdue ?? 0) > 0 && (
                        <>
                          <span className="text-gray-300">·</span>
                          <span className="text-red-600 font-medium">{obligationsData?.overdue ?? 0} overdue</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Governance Traceability — linked policies and rules */}
                <GovernanceTraceabilityCard contractId={contractId} />

                {/* Collapsible: Contract Details */}
                <CollapsibleSection title="Contract Details" icon={FileText} defaultOpen={false}>
                  {[
                    { label: "Vendor", value: contract.vendor, icon: Building2, missing: "Extraction Pending" },
                    { label: "Counterparty", value: contract.counterparty, icon: User, missing: "Extraction Pending" },
                    { label: "Type", value: contract.contract_type, icon: FileText, missing: "Not Found In Contract" },
                    { label: "Business Unit", value: contract.business_unit, missing: "Not Mapped" },
                    { label: "Geography", value: contract.geography, icon: Globe, missing: "Not Mapped" },
                    { label: "Owner", value: contract.owner, icon: User, missing: "Not Assigned" },
                    { label: "Status", value: (contract.status || "—").replace(/_/g, " ") },
                    { label: "Workflow Stage", value: contract.workflow_stage?.replace(/_/g, " ") ?? "—" },
                    { label: "Financial Value", value: contract.financial_value != null && contract.financial_value > 0 ? `${contract.currency ?? ""} ${contract.financial_value.toLocaleString()}` : "—", icon: DollarSign, missing: "Not Found In Contract" },
                    { label: "Auto-Renewal", value: contract.auto_renew ? "Yes" : "No" },
                    { label: "Has DPA", value: contract.has_dpa ? "Yes" : "No" },
                  ].map((row, i) => {
                    const displayValue = row.missing && (!row.value || row.value === "" || row.value === "0")
                      ? <span className="italic text-gray-400 dark:text-gray-500">{row.missing}</span>
                      : row.value;
                    return (
                      <div key={i} className="flex items-center justify-between px-4 py-1.5">
                        <span className="text-[10px] text-gray-500 dark:text-gray-400 flex items-center gap-1">
                          {row.icon && <row.icon className="w-3 h-3" />}{row.label}
                        </span>
                        <span className="text-[10px] font-medium text-gray-800 dark:text-gray-200 text-right max-w-[60%] truncate">{displayValue}</span>
                      </div>
                    );
                  })}
                </CollapsibleSection>

                {/* Collapsible: Key Dates */}
                <CollapsibleSection title="Key Dates" icon={Calendar} defaultOpen={false}>
                  {[
                    { label: "Effective", value: formatDate(contract.effective_date) },
                    { label: "Expiration", value: formatDate(contract.expiration_date) },
                    { label: "Renewal", value: formatDate(contract.renewal_date) },
                    { label: "Last Activity", value: formatDate(contract.last_activity) },
                    { label: "Created", value: formatDate(contract.created_at) },
                  ].map((row, i) => (
                    <div key={i} className="flex items-center justify-between px-4 py-1.5">
                      <span className="text-[10px] text-gray-500">{row.label}</span>
                      <span className="text-[10px] font-medium text-gray-800 dark:text-gray-200">{row.value}</span>
                    </div>
                  ))}
                </CollapsibleSection>

                {/* Collapsible: Tags */}
                {contract.tags.length > 0 && (
                  <CollapsibleSection title="Tags" icon={Tag} defaultOpen={false} badge={contract.tags.length}>
                    <div className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {contract.tags.map(tag => (
                          <span key={tag} className="text-[9px] px-2 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-700 dark:text-navy-200">{tag}</span>
                        ))}
                      </div>
                    </div>
                  </CollapsibleSection>
                )}

                {/* Collapsible: Obligations */}
                <CollapsibleSection
                  title="Obligations"
                  icon={ListChecks}
                  defaultOpen={true}
                  badge={obligationsData?.total ?? obligations.length}
                >
                  {obligations.length === 0 ? (
                    <div className="px-4 py-3 text-[10px] text-gray-400 italic">No obligations tracked.</div>
                  ) : obligations.slice(0, 8).map(ob => (
                    <div
                      key={ob.id}
                      onClick={() => router.push(`/obligations?obligationId=${ob.id}`)}
                      className="flex items-start gap-2 px-4 py-2 hover:bg-gray-50 dark:hover:bg-navy-750 cursor-pointer transition-colors"
                    >
                      <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                        ob.status === "overdue" ? "bg-red-500" : ob.status === "completed" ? "bg-green-500" : ob.status === "in_progress" ? "bg-blue-500" : "bg-yellow-500"
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] text-gray-700 dark:text-gray-300 truncate">{ob.description}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
                            ob.status === "overdue" ? "bg-red-100 text-red-700" : ob.status === "completed" ? "bg-green-100 text-green-700" : ob.status === "in_progress" ? "bg-blue-100 text-blue-700" : "bg-yellow-100 text-yellow-700"
                          }`}>{ob.status.replace(/_/g, " ")}</span>
                          <span className="text-[8px] text-gray-400">Due: {formatDate(ob.due_date)}</span>
                          <span className="text-[8px] text-gray-400">{ob.owner}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </CollapsibleSection>

                {/* ── Intelligence Hub ─────────────────────────────────────
                    Single-screen summary of the contract's risk profile,
                    findings, clauses, policy, related reviews and
                    obligations. Lets reviewers triage without leaving the
                    Overview tab. */}
                <IntelligenceHub
                  findings={findings}
                  clauses={clauses}
                  obligations={obligations}
                  contractId={contractId}
                  riskScore={contract.risk_score ?? 0}
                  findingCount={contract.ai_findings_count ?? findings.length}
                />
              </div>
            )}

            {activeTab === "insights" && (
              <div className="space-y-3">
                {/* AI Confidence & Summary */}
                <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-gradient-to-br from-purple-50 to-white dark:from-navy-800 dark:to-navy-850">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Brain className="w-3.5 h-3.5 text-purple-500" />
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">AI Detection</span>
                  </div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs text-gray-500">Confidence</span>
                    <div className="flex-1 h-2 bg-gray-200 dark:bg-navy-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${(contract.confidence_score ?? 0) >= 0.7 ? "bg-green-500" : (contract.confidence_score ?? 0) >= 0.4 ? "bg-amber-500" : "bg-red-500"}`}
                        style={{ width: `${(contract.confidence_score ?? 0) * 100}%` }} />
                    </div>
                    <span className="text-[10px] font-bold text-navy-900 dark:text-white">{Math.round((contract.confidence_score ?? 0) * 100)}%</span>
                  </div>
                  {contract.ai_summary && (
                    <p className="text-[10px] text-gray-700 dark:text-gray-300 leading-relaxed">{contract.ai_summary}</p>
                  )}
                </div>

                {/* AI Findings */}
                <div className="rounded-lg border border-gray-200 dark:border-navy-700">
                  <div className="px-3 py-2 border-b border-gray-100 dark:border-navy-700 bg-gray-50 dark:bg-navy-850 flex items-center justify-between">
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">AI Findings ({findings.length})</span>
                    <button onClick={openAiReview} className="text-[8px] font-medium text-blue-600 hover:text-blue-700">View all in Review →</button>
                  </div>
                  {findings.length === 0 ? (
                    <div className="px-3 py-4 text-[10px] text-gray-400 italic">No AI findings yet. Run AI analysis to detect risks.</div>
                  ) : (
                    <div className="divide-y divide-gray-50 dark:divide-navy-800">
                      {findings.slice(0, 10).map(f => (
                        <div key={f.id} className="flex items-start gap-2 px-3 py-2">
                          <span className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${
                            f.severity === "critical" ? "bg-red-500" : f.severity === "high" ? "bg-orange-500" : f.severity === "medium" ? "bg-amber-500" : "bg-gray-400"
                          }`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] font-medium text-navy-900 dark:text-white">{f.title}</span>
                              <span className={`text-[7px] px-1 py-0.5 rounded font-medium ${
                                f.severity === "critical" ? "bg-red-100 text-red-700" : f.severity === "high" ? "bg-orange-100 text-orange-700" : f.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600"
                              }`}>{f.severity}</span>
                            </div>
                            <p className="text-[9px] text-gray-500 mt-0.5 line-clamp-2">{f.description}</p>
                            {f.recommendation && (
                              <p className="text-[8px] text-blue-600 mt-0.5">{f.recommendation}</p>
                            )}
                          </div>
                          {f.confidence != null && (
                            <span className="text-[8px] text-gray-400 flex-shrink-0">{Math.round(f.confidence * 100)}%</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* AI Flags */}
                {contract.ai_flags.length > 0 && (
                  <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/10 p-3">
                    <span className="text-[9px] font-semibold text-amber-700 dark:text-amber-300 uppercase">AI Flags</span>
                    <div className="mt-1 space-y-1">
                      {contract.ai_flags.map(flag => (
                        <div key={flag} className="flex items-center gap-1.5 text-[9px] text-amber-600">
                          <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0" /> {flag.replace(/_/g, " ")}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "clauses" && (
              <div className="space-y-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] font-semibold text-gray-500 uppercase">Clause Analysis ({clauses.length})</span>
                  <span className="text-[8px] text-gray-400">{contract.clause_count} total clauses</span>
                </div>
                {clauses.length === 0 ? (
                  <div className="text-center py-8 text-xs text-gray-400">No clause analysis data available.</div>
                ) : (
                  <div className="space-y-1.5">
                    {clauses.map(c => (
                      <div key={c.id} className="flex items-start gap-2 p-2.5 rounded-lg border border-gray-200 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="text-[10px] font-semibold text-navy-900 dark:text-white capitalize">{c.clause_type.replace(/_/g, " ")}</span>
                            <span className={`text-[7px] px-1 py-0.5 rounded font-medium ${
                              c.severity === "critical" ? "bg-red-100 text-red-700" : c.severity === "high" ? "bg-orange-100 text-orange-700" : c.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"
                            }`}>{c.severity}</span>
                          </div>
                          <div className="grid grid-cols-2 gap-1 mt-1">
                            <div className="p-1.5 rounded bg-green-50 dark:bg-green-900/10 border border-green-100 dark:border-green-800">
                              <span className="text-[7px] font-semibold text-green-700 uppercase">Expected</span>
                              <p className="text-[8px] text-gray-600 mt-0.5">{c.expected}</p>
                            </div>
                            <div className="p-1.5 rounded bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-800">
                              <span className="text-[7px] font-semibold text-red-700 uppercase">Actual</span>
                              <p className="text-[8px] text-gray-600 mt-0.5">{c.actual}</p>
                            </div>
                          </div>
                          {c.recommendation && (
                            <p className="text-[8px] text-blue-600 mt-1">{c.recommendation}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "activity" && (
              <div className="space-y-2">
                {activityEvents.length === 0 ? (
                  <div className="text-center py-8 text-xs text-gray-400">No activity recorded for this contract.</div>
                ) : (
                  <AuditTrailPanel
                    events={activityEvents.map((e) => ({
                      id: e.id,
                      type: e.type,
                      actor: e.actor,
                      role: undefined,
                      action: e.action,
                      timestamp: e.timestamp,
                      previous_value: undefined,
                      new_value: undefined,
                      reason: e.details,
                    }))}
                  />
                )}
              </div>
            )}

            {activeTab === "versions" && (
              <div className="space-y-2">
                {versions.length === 0 ? (
                  <div className="text-center py-8 text-xs text-gray-400">No version history available.</div>
                ) : (
                  versions.map(v => (
                    <div key={v.id} className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${v.status === "current" ? "bg-green-500" : v.status === "finalized" ? "bg-blue-500" : "bg-gray-400"}`} />
                        <div>
                          <p className="text-[11px] font-medium text-navy-900 dark:text-white">v{v.version_number} {v.label && `- ${v.label}`}</p>
                          <p className="text-[9px] text-gray-400">{v.uploaded_by} · {formatDate(v.uploaded_at)} · {v.page_count} pages</p>
                        </div>
                      </div>
                      <button className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400"><Download className="w-3.5 h-3.5" /></button>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "reviews" && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-semibold text-gray-500 uppercase">Related Reviews</span>
                </div>
                <RelatedReviewsPanel contractId={contractId} />
              </div>
            )}

            {activeTab === "workflow" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[9px] font-semibold text-gray-500 uppercase">Workflow Timeline</span>
                    <p className="text-[10px] text-gray-400 mt-0.5">Status changes, assignments, escalations and approvals in audit order.</p>
                  </div>
                </div>
                <WorkflowTimelinePanel events={workflowTimeline} />
              </div>
            )}

            {activeTab === "lifecycle" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-semibold text-gray-500 uppercase">Lifecycle History</span>
                </div>
                <LifecycleHistoryPanel events={activityEvents} />
              </div>
            )}

            {activeTab === "signatures" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-semibold text-gray-500 uppercase">Signature Requests</span>
                  {(contract.status === "finalized" || contract.status === "approved" || contract.status === "active") && (
                    <button
                      onClick={async () => {
                        setActionLoading("sign");
                        try {
                          await api.post("/signatures", {
                            contract_id: contractId,
                            title: `Sign: ${contract.name || contract.filename || contractId}`,
                            provider: "docusign",
                            signers: [{ email: "signer@contractriskedge.com", name: "Contract Signer", role: "signer", signing_order: 1 }],
                            email_subject: `Please sign: ${contract.name || contract.filename || "Contract"}`,
                            email_message: "This document is ready for your electronic signature via DocuSign.",
                          });
                          alert("Signature request created!");
                          refetch();
                        } catch (err: any) {
                          alert(`Failed: ${err?.message || "Unknown error"}`);
                        } finally {
                          setActionLoading(null);
                        }
                      }}
                      disabled={actionLoading === "sign"}
                      className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-colors shadow-sm"
                    >
                      {actionLoading === "sign" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSignature className="w-3.5 h-3.5" />}
                      Send for Signature
                    </button>
                  )}
                </div>
                {(!signaturesData || signaturesData.length === 0) ? (
                  <div className="text-center py-12 text-gray-400">
                    <FileSignature className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p className="text-xs">No signature requests for this contract</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {signaturesData.map((sig: any) => (
                      <div key={sig.id} className="border border-gray-200 dark:border-navy-700 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{sig.title}</h4>
                          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                            sig.status === "completed" ? "bg-green-100 text-green-700" :
                            sig.status === "sent" ? "bg-purple-100 text-purple-700" :
                            sig.status === "declined" ? "bg-red-100 text-red-700" :
                            "bg-gray-100 text-gray-600"
                          }`}>{sig.status}</span>
                        </div>
                        <div className="text-xs text-gray-500 space-y-1">
                          <p>Provider: {sig.provider}</p>
                          {sig.provider_reference && <p>Envelope: {sig.provider_reference}</p>}
                          <p>Created: {new Date(sig.created_at).toLocaleDateString()}</p>
                        </div>
                        {sig.signers?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {sig.signers.map((s: any) => (
                              <span key={s.id} className={`text-[10px] px-2 py-0.5 rounded-md ${
                                s.status === "signed" ? "bg-green-50 text-green-700" :
                                s.status === "declined" ? "bg-red-50 text-red-700" :
                                "bg-gray-50 text-gray-500"
                              }`}>{s.name} ({s.email}) - {s.status}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Approval Modal ── */}
      {approvalModalOpen && (
        <ApprovalModal
          reviewId={contractId}
          reviewTitle={contract.name}
          riskScore={contract.risk_score != null ? contract.risk_score / 10 : undefined}
          openCriticalFindings={openCriticalFindings}
          openObligations={openObligations}
          onApprove={async (decision, comment, conditions) => {
            setActionLoading("approve");
            await approveMut.mutateAsync({ decision, comment, conditions });
          }}
          onReject={async (comment, category, severity) => {
            setActionLoading("reject");
            await rejectMut.mutateAsync({ comment, category, severity });
          }}
          onClose={() => setApprovalModalOpen(false)}
          isLoading={approveMut.isPending || rejectMut.isPending}
        />
      )}

      {/* ── Close Modal ── */}
      {closeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => { setCloseModalOpen(false); setCloseReason(""); }}>
          <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-sm mx-4 p-5" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-navy-900">Close Contract</h3>
            <p className="text-[11px] text-gray-500 mt-1">Close "{contract.name}"? This will archive the contract and end its lifecycle.</p>
            <p className="text-[10px] text-amber-600 mt-1">Open obligations will block this action.</p>
            <div className="mt-3">
              <label className="text-[10px] font-semibold text-gray-600">Reason for closing <span className="text-red-500">*</span></label>
              <textarea
                value={closeReason}
                onChange={e => setCloseReason(e.target.value)}
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
              <button
                onClick={() => { setCloseModalOpen(false); setCloseReason(""); }}
                className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleClose}
                disabled={closeMut.isPending || closeReason.trim().length < 5}
                className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-gray-700 text-white hover:bg-gray-800 disabled:opacity-50"
              >
                {closeMut.isPending ? "Closing..." : "Close Contract"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Governance Traceability Card ──────────────────────────────────────────

function GovernanceTraceabilityCard({ contractId }: { contractId: string }) {
  // The contract ID maps to a review ID 1:1. Fetch governance data from
  // the risk-breakdown endpoint which now includes governance_traceability.
  const { data, isLoading, isError } = useRiskBreakdown(contractId);
  const traceability: GovernanceTraceability | undefined = data?.governance_traceability;
  const [expanded, setExpanded] = useState(false);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50 dark:border-indigo-800 dark:from-indigo-900/10 dark:to-blue-900/10 p-3 animate-pulse">
        <div className="h-3 w-24 bg-indigo-200 rounded mb-2" />
        <div className="h-8 w-full bg-indigo-100 rounded" />
      </div>
    );
  }

  if (isError || !traceability || traceability.linked_policy_count === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50 dark:border-indigo-800 dark:from-indigo-900/10 dark:to-blue-900/10 p-3">
      <div className="flex items-center gap-1.5 mb-2">
        <GitBranch className="w-3.5 h-3.5 text-indigo-700 dark:text-indigo-400" />
        <span className="text-[9px] font-semibold uppercase tracking-wider text-indigo-800 dark:text-indigo-300">
          Governance Traceability
        </span>
      </div>

      {/* Full chain counts */}
      <div className="grid grid-cols-3 gap-1.5 mb-2">
        <div className="rounded-md border border-indigo-200 bg-white/70 dark:border-indigo-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Policies</p>
          <p className="text-sm font-bold text-indigo-700 dark:text-indigo-300 tabular-nums">{traceability.linked_policy_count}</p>
        </div>
        <div className="rounded-md border border-blue-200 bg-white/70 dark:border-blue-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider">Rules</p>
          <p className="text-sm font-bold text-blue-700 dark:text-blue-300 tabular-nums">{traceability.linked_rule_count}</p>
        </div>
        <div className="rounded-md border border-amber-200 bg-white/70 dark:border-amber-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-amber-600 dark:text-amber-400 uppercase tracking-wider">Requirements</p>
          <p className="text-sm font-bold text-amber-700 dark:text-amber-300 tabular-nums">{traceability.linked_requirement_count}</p>
        </div>
        <div className="rounded-md border border-red-200 bg-white/70 dark:border-red-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-red-600 dark:text-red-400 uppercase tracking-wider">Violations</p>
          <p className="text-sm font-bold text-red-700 dark:text-red-300 tabular-nums">{traceability.linked_violation_count}</p>
        </div>
        <div className="rounded-md border border-orange-200 bg-white/70 dark:border-orange-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-orange-600 dark:text-orange-400 uppercase tracking-wider">Findings</p>
          <p className="text-sm font-bold text-orange-700 dark:text-orange-300 tabular-nums">{traceability.linked_finding_count}</p>
        </div>
        <div className="rounded-md border border-rose-200 bg-white/70 dark:border-rose-800 dark:bg-navy-800/50 p-1.5 text-center">
          <p className="text-[7px] font-medium text-rose-600 dark:text-rose-400 uppercase tracking-wider">Redlines</p>
          <p className="text-sm font-bold text-rose-700 dark:text-rose-300 tabular-nums">{traceability.linked_redline_count}</p>
        </div>
      </div>

      {traceability.linked_policies.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-[9px] font-medium text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <span>{traceability.linked_policies.length} polic{traceability.linked_policies.length === 1 ? "y" : "ies"} applied</span>
          </button>

          {expanded && (
            <div className="mt-2 space-y-1">
              {traceability.linked_policies.map((policy) => (
                <div
                  key={policy.playbook_id}
                  className="flex items-center gap-2 rounded-md bg-white/60 dark:bg-navy-800/30 px-2 py-1.5 text-[9px]"
                >
                  <BookOpen className="w-2.5 h-2.5 text-indigo-500 flex-shrink-0" />
                  <span className="font-medium text-gray-700 dark:text-gray-300 truncate">
                    {policy.name}
                  </span>
                  {policy.version_label && (
                    <span className="ml-auto text-[7px] font-semibold px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 flex-shrink-0">
                      v{policy.version_label}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Traceability chain summary */}
      <div className="mt-2 pt-2 border-t border-indigo-200/50 dark:border-indigo-800/50">
        <div className="flex items-center justify-between text-[7px] text-gray-500 dark:text-gray-400">
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-indigo-500" /> Policy</span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Rule</span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> Req.</span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-500" /> Violation</span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-orange-500" /> Finding</span>
          <span className="text-indigo-300">→</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-rose-500" /> Redline</span>
        </div>
      </div>
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const EVENT_ICONS: Record<string, React.ElementType> = {
  contract_created: FileText, contract_uploaded: FileText, ai_analysis_started: Brain,
  ai_analysis_completed: Brain, finding_resolved: CheckCircle2, finding_dismissed: XCircle,
  comment_added: MessageSquare, review_assigned: User, review_approved: CheckCircle2,
  review_rejected: XCircle, status_changed: Activity, obligation_updated: Calendar,
  renewal_approaching: AlertTriangle, version_created: FileText, metadata_updated: FileText,
};

function formatTime(ts: string): string {
  if (!ts) return "—";
  const t = new Date(ts).getTime();
  if (Number.isNaN(t)) return "—";
  const diff = Date.now() - t;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

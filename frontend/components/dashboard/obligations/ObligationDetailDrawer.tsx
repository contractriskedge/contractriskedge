"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { X, ClipboardCheck, Clock, AlertTriangle, DollarSign, Activity, Shield, FileText, User, Calendar, Brain, Link, ExternalLink, Loader2, CheckCircle2, XCircle, RotateCcw, Archive, Paperclip, Edit3, Eye } from "lucide-react";
import type { ObligationRecord } from "./types";
import type { ObligationAuditLogResponse } from "@/services/api/obligations";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, STATUS_CONFIG, OBLIGATION_TYPES } from "./types";
import { obligationsService } from "@/services/api/obligations";
import { CompleteObligationModal } from "./CompleteObligationModal";

type TabId = "overview" | "sla" | "financial" | "compliance" | "ai" | "activity";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

interface DrawerProps {
  obligation: ObligationRecord | null;
  onClose: () => void;
  onToggleFavorite?: (id: string) => void;
  onStatusChange?: (id: string, status: string) => void;
}

export function ObligationDetailDrawer({ obligation, onClose, onToggleFavorite, onStatusChange }: DrawerProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<TabId>("overview");
  const [editMode, setEditMode] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [showStatusMenu, setShowStatusMenu] = useState(false);
  const [statusReason, setStatusReason] = useState("");
  const [pendingStatus, setPendingStatus] = useState<string | null>(null);
  const [showStatusReasonModal, setShowStatusReasonModal] = useState(false);
  const statusMenuRef = useRef<HTMLDivElement>(null);

  // Close status menu on outside click
  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (statusMenuRef.current && !statusMenuRef.current.contains(e.target as Node)) {
        setShowStatusMenu(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const statusOptions = [
    { value: "pending", label: "Pending", color: "text-yellow-700 bg-yellow-50" },
    { value: "in_progress", label: "In Progress", color: "text-blue-700 bg-blue-50" },
    { value: "pending_supplier", label: "Pending Supplier", color: "text-purple-700 bg-purple-50" },
    { value: "completed", label: "Completed", color: "text-green-700 bg-green-50" },
    { value: "cancelled", label: "Cancelled", color: "text-gray-600 bg-gray-100" },
    { value: "waived", label: "Waived", color: "text-gray-600 bg-gray-100" },
  ];

  // ── Status Change Mutation ──
  const statusMut = useMutation({
    mutationFn: ({ id, status, reason }: { id: string; status: string; reason?: string }) => {
      const payload: Record<string, unknown> = { status };
      if (reason?.trim()) payload.notes = reason.trim();
      return obligationsService.updateObligation(id, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      queryClient.invalidateQueries({ queryKey: ["obligations", "kpis"] });
      queryClient.invalidateQueries({ queryKey: ["obligation-audit"] });
      setShowStatusMenu(false);
      setShowStatusReasonModal(false);
      setStatusReason("");
      setPendingStatus(null);
    },
  });

  // ── Action Mutations ──────────────────────────────────────────
  const completeMut = useMutation({
    mutationFn: (id: string) => obligationsService.completeObligation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      setActionLoading(null);
    },
    onError: () => setActionLoading(null),
  });
  const cancelMut = useMutation({
    mutationFn: (id: string) => obligationsService.cancelObligation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      setActionLoading(null);
    },
    onError: () => setActionLoading(null),
  });
  const reopenMut = useMutation({
    mutationFn: (id: string) => obligationsService.reopenObligation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      setActionLoading(null);
    },
    onError: () => setActionLoading(null),
  });
  const archiveMut = useMutation({
    mutationFn: (id: string) => obligationsService.archiveObligation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      setActionLoading(null);
    },
    onError: () => setActionLoading(null),
  });

  const handleAction = (action: string, id: string) => {
    setActionLoading(action);
    if (action === "complete") completeMut.mutate(id);
    else if (action === "cancel") cancelMut.mutate(id);
    else if (action === "reopen") reopenMut.mutate(id);
    else if (action === "archive") archiveMut.mutate(id);
  };

  const isPending = (a: string) => actionLoading === a || completeMut.isPending || cancelMut.isPending || reopenMut.isPending || archiveMut.isPending;

  return (
    <AnimatePresence>
      {obligation && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
          <motion.div initial={{ opacity: 0, x: 380 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 380 }}
            transition={{ type: "spring", damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-[480px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center"><ClipboardCheck className="w-4 h-4 text-white" /></div>
                <div className="min-w-0"><h3 className="text-sm font-semibold text-navy-900 truncate">{obligation.name}</h3><p className="text-[10px] text-gray-500">{obligation.obligationNumber || obligation.id.slice(0, 8)} • {obligation.vendor}</p></div>
              </div>
              <div className="flex items-center gap-1">
                {/* Status Change Dropdown */}
                <div className="relative" ref={statusMenuRef}>
                  <button
                    onClick={(e) => { e.stopPropagation(); setShowStatusMenu(!showStatusMenu); }}
                    className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-navy-100 text-navy-700 hover:bg-navy-200 transition-colors"
                    title="Change status"
                  >
                    {statusMut.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
                    Status
                  </button>
                  {showStatusMenu && (
                    <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-xl z-50 py-1">
                      {statusOptions.filter(o => o.value !== obligation.status).map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => {
                            setShowStatusMenu(false);
                            setPendingStatus(opt.value);
                            setStatusReason("");
                            setShowStatusReasonModal(true);
                          }}
                          className={`w-full text-left px-3 py-1.5 text-[10px] hover:bg-gray-50 flex items-center gap-2`}
                        >
                          <span className={`w-2 h-2 rounded-full ${opt.color.split(" ")[0].replace("text-", "bg-")}`} />
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {/* Edit Toggle */}
                <button
                  onClick={() => setEditMode(!editMode)}
                  className={`flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded transition-colors ${
                    editMode ? "bg-navy-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                  title={editMode ? "View mode" : "Edit obligation"}
                >
                  {editMode ? <Eye className="w-3 h-3" /> : <Edit3 className="w-3 h-3" />}
                  {editMode ? "View" : "Edit"}
                </button>
                {/* Action Buttons */}
                {obligation.status !== "completed" && obligation.status !== "cancelled" && obligation.status !== "archived" && (
                  <button onClick={() => setShowCompleteModal(true)} disabled={isPending("complete")}
                    className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-green-100 text-green-700 hover:bg-green-200 disabled:opacity-50 transition-colors"
                    title="Mark as completed with evidence">
                    {isPending("complete") ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                    Complete
                  </button>
                )}
                {obligation.status !== "archived" && (
                  <button onClick={() => handleAction("archive", obligation.id)} disabled={isPending("archive")}
                    className="flex items-center gap-1 px-2 py-1 text-[9px] font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-50 transition-colors"
                    title="Archive obligation">
                    {isPending("archive") ? <Loader2 className="w-3 h-3 animate-spin" /> : <Archive className="w-3 h-3" />}
                    Archive
                  </button>
                )}
                <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400"><X className="w-4 h-4" /></button>
              </div>
            </div>
            <div className="flex items-center justify-between px-5 py-2 border-b border-gray-100 bg-gray-50/50">
              <div className="flex gap-1 overflow-x-auto">
                <TabBtn label="Overview" icon={<FileText className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
                <TabBtn label="SLA" icon={<Clock className="w-3 h-3" />} active={tab === "sla"} onClick={() => setTab("sla")} />
                <TabBtn label="Financial" icon={<DollarSign className="w-3 h-3" />} active={tab === "financial"} onClick={() => setTab("financial")} />
                <TabBtn label="Compliance" icon={<Shield className="w-3 h-3" />} active={tab === "compliance"} onClick={() => setTab("compliance")} />
                <TabBtn label="AI" icon={<Brain className="w-3 h-3" />} active={tab === "ai"} onClick={() => setTab("ai")} />
                <TabBtn label="Activity" icon={<Activity className="w-3 h-3" />} active={tab === "activity"} onClick={() => setTab("activity")} />
              </div>
              <button
                onClick={() => router.push(`/obligations/${obligation.id}`)}
                className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700 transition-colors flex-shrink-0"
                title="Open full workspace"
              >
                <ExternalLink className="w-3 h-3" />
                Full Workspace
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {tab === "overview" && (editMode ? <EditOverviewTab o={obligation} onClose={onClose} /> : <OverviewTab o={obligation} />)}
              {tab === "sla" && <SlaTab o={obligation} />}
              {tab === "financial" && <FinancialTab o={obligation} />}
              {tab === "compliance" && <ComplianceTab />}
              {tab === "ai" && <AiTab o={obligation} />}
              {tab === "activity" && <ActivityTab obligationId={obligation.id} />}
            </div>
          </motion.div>
        </>

      )}

      {/* Complete Obligation Modal */}
      {showCompleteModal && (
        <CompleteObligationModal
          obligationId={obligation.id}
          obligationName={obligation.name}
          currentUserName={obligation.assignee || "Current User"}
          onComplete={() => {
            queryClient.invalidateQueries({ queryKey: ["obligations"] });
            queryClient.invalidateQueries({ queryKey: ["obligations", "kpis"] });
            queryClient.invalidateQueries({ queryKey: ["obligations", "overdue"] });
            queryClient.invalidateQueries({ queryKey: ["obligations", "upcoming"] });
            setShowCompleteModal(false);
          }}
          onClose={() => setShowCompleteModal(false)}
        />
      )}

      {/* Status Change Reason Modal */}
      <AnimatePresence>
        {showStatusReasonModal && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => { setShowStatusReasonModal(false); setPendingStatus(null); }}>
            <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
              className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-sm mx-4 p-5" onClick={e => e.stopPropagation()}>
              <h3 className="text-sm font-semibold text-navy-900">Change Status</h3>
              <p className="text-[11px] text-gray-500 mt-1">
                {obligation.name} — <span className="font-medium text-navy-700">{statusOptions.find(o => o.value === pendingStatus)?.label}</span>
              </p>
              <div className="mt-3">
                <label className="text-[10px] font-semibold text-gray-600">Reason for change <span className="text-red-500">*</span></label>
                <textarea
                  value={statusReason}
                  onChange={e => setStatusReason(e.target.value)}
                  placeholder="Enter the reason for this status change..."
                  rows={3}
                  className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400 resize-none"
                  autoFocus
                />
                {statusReason.trim().length > 0 && statusReason.trim().length < 5 && (
                  <p className="text-[9px] text-red-500 mt-0.5">Please enter at least 5 characters</p>
                )}
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button onClick={() => { setShowStatusReasonModal(false); setPendingStatus(null); setStatusReason(""); }}
                  className="px-3 py-1.5 text-[10px] font-medium text-gray-600 hover:text-gray-800 rounded-lg hover:bg-gray-50 transition-colors">
                  Cancel
                </button>
                <button
                  onClick={() => {
                    if (pendingStatus && statusReason.trim().length >= 5) {
                      statusMut.mutate({ id: obligation.id, status: pendingStatus, reason: statusReason.trim() });
                      onStatusChange?.(obligation.id, pendingStatus);
                    }
                  }}
                  disabled={!pendingStatus || statusReason.trim().length < 5 || statusMut.isPending}
                  className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-navy-600 text-white hover:bg-navy-700 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1 transition-colors"
                >
                  {statusMut.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                  Confirm
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </AnimatePresence>
  );
}

/** Format ISO timestamp to user-friendly date (e.g., "Jun 10, 2026"). */
function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
}

function OverviewTab({ o }: { o: ObligationRecord }) {
  const router = useRouter();
  const sc = STATUS_CONFIG[o.status];
  const MetaRow = ({ label, value, icon }: { label: string; value: string | React.ReactNode; icon?: React.ReactNode }) => (
    <div className="flex items-center justify-between py-1.5"><span className="text-[11px] text-gray-500 flex items-center gap-1.5">{icon}{label}</span><span className="text-[11px] font-medium text-gray-800">{value}</span></div>
  );
  return (
    <div className="space-y-4">
      {/* Linked Contract Card */}
      {o.contractId && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-100 dark:border-blue-800">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[9px] font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wider">Linked Contract</span>
            <button
              onClick={() => router.push(`/contracts/${o.contractId}`)}
              className="text-[9px] font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 inline-flex items-center gap-0.5"
            >
              View <ExternalLink className="w-2.5 h-2.5" />
            </button>
          </div>
          <p className="text-[11px] font-semibold text-navy-900 dark:text-white truncate">{o.contractName || o.contractId.slice(0, 8)}</p>
          <div className="flex items-center gap-2 mt-1 text-[9px] text-gray-500">
            {o.contractNumber && <span className="font-mono">{o.contractNumber}</span>}
            {o.vendor && <span>Vendor: {o.vendor}</span>}
            {o.contractOwner && (
              <>
                <span className="text-gray-300">·</span>
                <span>Owner: {o.contractOwner}</span>
              </>
            )}
          </div>
        </div>
      )}

      <div className="p-3 bg-navy-50 rounded-lg border border-navy-100">
        <p className="text-[10px] font-semibold text-navy-700 uppercase mb-1">Description</p>
        <p className="text-[11px] text-gray-700 leading-relaxed">{o.description}</p>
      </div>
      <div className="bg-gray-50 rounded-lg p-3 space-y-0.5 divide-y divide-gray-100">
        <MetaRow label="Status" value={<span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${sc.bg} ${sc.color}`}>{sc.label}</span>} />
        <MetaRow label="Type" value={OBLIGATION_TYPES.find((t) => t.id === o.type)?.label || o.type} />
        <MetaRow label="Contract" value={
          o.contractId ? (
            <button onClick={() => router.push(`/contracts/${o.contractId}`)} className="text-[10px] text-blue-600 hover:text-blue-800 inline-flex items-center gap-0.5">
              {o.contractName || o.contractId.slice(0, 8)} <ExternalLink className="w-2.5 h-2.5" />
            </button>
          ) : (o.contractName || "—")
        } icon={<FileText className="w-3 h-3" />} />
        <MetaRow label="Vendor" value={o.vendor} />
        <MetaRow label="Owner" value={o.owner} icon={<User className="w-3 h-3" />} />
        <MetaRow label="Assignee" value={o.assignee} />
        <MetaRow label="Due Date" value={fmtDate(o.dueDate)} icon={<Calendar className="w-3 h-3" />} />
        {o.completedDate && <MetaRow label="Completed" value={fmtDate(o.completedDate)} icon={<Calendar className="w-3 h-3" />} />}
        <MetaRow label="Risk Score" value={<RiskBadge score={o.riskScore} />} />
        <MetaRow label="Financial Impact" value={`$${o.financialImpact.toLocaleString()}`} icon={<DollarSign className="w-3 h-3" />} />
        <MetaRow label="Clause Reference" value={
          o.clauseReference ? (
            <button onClick={() => router.push(`/clause-library?search=${encodeURIComponent(o.clauseReference)}`)} className="text-[10px] text-blue-600 hover:text-blue-800 inline-flex items-center gap-0.5">
              {o.clauseReference} <ExternalLink className="w-2.5 h-2.5" />
            </button>
          ) : "—"
        } />
        <MetaRow label="Department" value={o.department} />
        <MetaRow label="Business Unit" value={o.businessUnit} />
        <MetaRow label="Geography" value={o.geography} />
        <MetaRow label="Escalation Level" value={o.escalationLevel > 0 ? `Level ${o.escalationLevel}` : "None"} />
        <MetaRow label="Attachments" value={o.attachments.toString()} />
      </div>

      {/* Completion Information — only shown when completed */}
      {o.status === "completed" && (
        <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wider">Completion Information</span>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500 flex items-center gap-1"><User className="w-3 h-3" /> Completed By</span>
              <span className="text-[10px] font-medium text-gray-800">{o.completedBy || "—"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500 flex items-center gap-1"><Calendar className="w-3 h-3" /> Completion Date</span>
              <span className="text-[10px] font-medium text-gray-800">{fmtDate(o.completedDate) || "—"}</span>
            </div>
            {o.completionNotes && (
              <div className="pt-2 border-t border-emerald-200">
                <span className="text-[10px] text-gray-500 block mb-1">Completion Notes</span>
                <p className="text-[11px] text-gray-700 leading-relaxed bg-white rounded p-2 border border-emerald-100">
                  {o.completionNotes}
                </p>
              </div>
            )}
            {(o.evidenceAttachmentCount ?? 0) > 0 && (
              <EvidenceFilesList obligationId={o.id} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Fetches and displays clickable evidence file list for a completed obligation. */
function EvidenceFilesList({ obligationId }: { obligationId: string }) {
  const { data: evidence, isLoading } = useQuery({
    queryKey: ["obligation-evidence", obligationId],
    queryFn: () => obligationsService.listEvidence(obligationId),
    enabled: !!obligationId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 pt-2 border-t border-emerald-200">
        <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
        <span className="text-[10px] text-gray-400">Loading evidence...</span>
      </div>
    );
  }

  const files = Array.isArray(evidence) ? evidence : [];

  if (files.length === 0) return null;

  return (
    <div className="pt-2 border-t border-emerald-200">
      <span className="text-[10px] text-gray-500 flex items-center gap-1 mb-1.5">
        <Paperclip className="w-3 h-3" /> Evidence Attachments ({files.length})
      </span>
      <div className="space-y-1">
        {files.map((f) => (
          <div key={f.id} className="flex items-center justify-between px-2 py-1.5 bg-white rounded border border-emerald-100">
            <div className="flex items-center gap-1.5 min-w-0">
              <FileText className="w-3 h-3 text-emerald-500 shrink-0" />
              {f.file_url ? (
                <a
                  href={f.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-blue-600 hover:text-blue-800 hover:underline truncate"
                  title={f.file_name}
                >
                  {f.file_name}
                </a>
              ) : (
                <span className="text-[10px] text-gray-700 truncate" title={f.file_name}>
                  {f.file_name}
                </span>
              )}
              <span className="text-[8px] text-gray-400 uppercase shrink-0">({f.file_type})</span>
            </div>
            {f.file_url && (
              <a
                href={f.file_url}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 text-gray-400 hover:text-blue-600"
                title="Download"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function SlaTab({ o }: { o: ObligationRecord }) {
  return (
    <div className="space-y-3">
      <div className={`p-3 rounded-lg border ${o.slaStatus === "breached" ? "bg-red-50 border-red-200" : o.slaStatus === "at_risk" ? "bg-orange-50 border-orange-200" : "bg-green-50 border-green-200"}`}>
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase">{o.slaStatus === "breached" ? "SLA Breached" : o.slaStatus === "at_risk" ? "At Risk" : "On Track"}</span>
          <span className="text-lg font-bold">{o.slaStatus === "breached" ? `${-o.slaRemaining}h breached` : `${o.slaRemaining}h remaining`}</span>
        </div>
      </div>
      <div className="p-4 bg-gray-50 rounded-lg text-center">
        <Activity className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-xs text-gray-500">SLA detail metrics not yet available</p>
        <p className="text-[10px] text-gray-400 mt-1">Real SLA performance data will appear once the monitoring pipeline is connected</p>
      </div>
    </div>
  );
}

function FinancialTab({ o }: { o: ObligationRecord }) {
  return (
    <div className="space-y-3">
      <div className="p-4 bg-gray-50 rounded-lg text-center">
        <p className="text-[10px] text-gray-500 uppercase font-semibold">Financial Impact</p>
        <p className="text-2xl font-bold text-navy-900 mt-1">{o.currency} {o.financialImpact.toLocaleString()}</p>
      </div>
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-center">
        <AlertTriangle className="w-6 h-6 text-amber-400 mx-auto mb-2" />
        <p className="text-xs text-amber-700 font-medium">Financial breakdown not configured</p>
        <p className="text-[10px] text-amber-600 mt-1">Overdue, at-risk, and recovered amounts require a financial impact model to be configured for this obligation type.</p>
      </div>
    </div>
  );
}

function ComplianceTab() {
  return (
    <div className="flex flex-col items-center py-8 text-center">
      <Shield className="w-10 h-10 text-gray-300 mb-3" />
      <p className="text-sm font-medium text-gray-500">Compliance tracking not yet available</p>
      <p className="text-xs text-gray-400 mt-1 max-w-xs">
        Compliance requirements and statuses will appear once the compliance monitoring framework is connected to this obligation.
      </p>
    </div>
  );
}

function AiTab({ o }: { o: ObligationRecord }) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
        <div className="flex items-center gap-1.5 mb-1.5"><Brain className="w-3.5 h-3.5 text-purple-600" /><span className="text-[10px] font-semibold text-purple-700 uppercase">AI Risk Assessment</span></div>
        <div className="space-y-2">
          {[
            { title: "Risk Prediction", desc: `AI predicts ${o.aiRiskPrediction}% probability of this obligation becoming overdue or breached.` },
            { title: "Recommended Action", desc: o.status === "overdue" ? "Escalate immediately. Send formal notice to vendor." : "Set reminder 7 days before due date. Monitor progress weekly." },
            { title: "Confidence", desc: `AI confidence: ${o.aiConfidence}%. Based on ${o.riskScore}/10 risk score and historical patterns.` },
            { title: "Impact Analysis", desc: `Financial impact of non-compliance: $${o.financialImpact.toLocaleString()}. ${o.escalationLevel > 0 ? `Currently at escalation level ${o.escalationLevel}.` : "No escalation triggered yet."}` },
          ].map((item) => (
            <div key={item.title} className="p-2 bg-white rounded border border-purple-100">
              <p className="text-[10px] font-semibold text-navy-700 uppercase mb-0.5">{item.title}</p>
              <p className="text-[11px] text-gray-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ActivityTab({ obligationId }: { obligationId: string }) {
  const { data: auditEntries, isLoading } = useQuery({
    queryKey: ["obligation-audit", obligationId],
    queryFn: () => obligationsService.getAuditHistory(obligationId),
    enabled: !!obligationId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
      </div>
    );
  }

  const entries = Array.isArray(auditEntries) ? auditEntries : [];

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <Activity className="w-8 h-8 text-gray-300 mb-2" />
        <p className="text-xs text-gray-400">No audit history available</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Activity History</p>
      {entries.map((a: ObligationAuditLogResponse, i: number) => (
        <div key={i} className="flex items-start gap-2 p-2 bg-white border border-gray-100 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-navy-400 mt-1.5 flex-shrink-0" />
          <div>
            <p className="text-[11px] text-gray-800">{a.action}</p>
            <p className="text-[9px] text-gray-400">
              {a.actor || "System"} • {(a.created_at || "").slice(0, 10)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

function RiskBadge({ score }: { score: number }) {
  const level = score >= 8 ? "critical" : score >= 6 ? "high" : score >= 4 ? "medium" : "low";
  return <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[level]} ${RISK_TEXT[level]}`}><span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[level]}`} />{score}/10</span>;
}

// ── Edit Overview Tab ────────────────────────────────────────────

function EditOverviewTab({ o, onClose }: { o: ObligationRecord; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(o.name);
  const [description, setDescription] = useState(o.description);
  const [owner, setOwner] = useState(o.owner);
  const [assignee, setAssignee] = useState(o.assignee);
  const [dueDate, setDueDate] = useState(o.dueDate);
  const [department, setDepartment] = useState(o.department);
  const [businessUnit, setBusinessUnit] = useState(o.businessUnit);
  const [geography, setGeography] = useState(o.geography);
  const [clauseReference, setClauseReference] = useState(o.clauseReference);
  const [financialImpact, setFinancialImpact] = useState(String(o.financialImpact));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await obligationsService.updateObligation(o.id, {
        name,
        description,
        owner,
        assignee,
        due_date: dueDate,
        department,
        business_unit: businessUnit,
        geography,
        clause_reference: clauseReference,
        financial_impact: parseFloat(financialImpact) || 0,
      } as Record<string, unknown>);
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      onClose();
    } catch (err) {
      console.error("Failed to save obligation:", err);
    } finally {
      setSaving(false);
    }
  };

  const inputClass = "w-full px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400 bg-white";

  return (
    <div className="space-y-3 p-1">
      <div>
        <label className="text-[10px] font-semibold text-gray-600">Name</label>
        <input type="text" value={name} onChange={e => setName(e.target.value)} className={inputClass} />
      </div>
      <div>
        <label className="text-[10px] font-semibold text-gray-600">Description</label>
        <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} className={inputClass} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] font-semibold text-gray-600">Owner</label>
          <input type="text" value={owner} onChange={e => setOwner(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-gray-600">Assignee</label>
          <input type="text" value={assignee} onChange={e => setAssignee(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-gray-600">Due Date</label>
          <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-gray-600">Financial Impact</label>
          <input type="number" value={financialImpact} onChange={e => setFinancialImpact(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-gray-600">Department</label>
          <input type="text" value={department} onChange={e => setDepartment(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-gray-600">Business Unit</label>
          <input type="text" value={businessUnit} onChange={e => setBusinessUnit(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-gray-600">Geography</label>
          <input type="text" value={geography} onChange={e => setGeography(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-gray-600">Clause Reference</label>
          <input type="text" value={clauseReference} onChange={e => setClauseReference(e.target.value)} className={inputClass} />
        </div>
      </div>
      <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
        <button onClick={onClose} className="px-3 py-1.5 text-[10px] font-medium text-gray-600 hover:text-gray-800">Cancel</button>
        <button onClick={handleSave} disabled={saving}
          className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-navy-600 text-white hover:bg-navy-700 disabled:opacity-50 inline-flex items-center gap-1">
          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
          Save Changes
        </button>
      </div>
    </div>
  );
}

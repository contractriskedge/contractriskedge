/**
 * Obligation Detail Page — Full-page workspace for a single obligation.
 *
 * Provides the same detail tabs as the ObligationDetailDrawer plus status
 * change, edit capabilities, and action buttons in a full-page layout.
 * Matches the pattern used by Contract Repository's /contracts/:id workspace.
 */

"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, ArrowLeft, ClipboardCheck, RotateCcw, CheckCircle2, Archive, Edit3, Eye, ExternalLink, FileText, Clock, DollarSign, Shield, Brain, Activity } from "lucide-react";
import { obligationsService } from "@/services/api/obligations";
import type { ObligationResponse } from "@/services/api/obligations";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT, STATUS_CONFIG, OBLIGATION_TYPES } from "@/components/dashboard/obligations/types";
import { ActivityTab } from "@/components/dashboard/obligations/ObligationDetailDrawer";

type TabId = "overview" | "sla" | "financial" | "compliance" | "ai" | "activity";

function TabBtn({ label, icon, active, onClick }: { label: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"}`}>
      {icon}{label}
    </button>
  );
}

function toObligationRecord(o: ObligationResponse) {
  return {
    id: o.id,
    obligationNumber: o.obligation_number || "",
    name: o.name,
    contractId: o.contract_uuid_id ?? o.contract_id ?? "",
    contractName: o.contract_name ?? "",
    contractNumber: (o as unknown as Record<string, unknown>).contract_number as string ?? "",
    vendor: o.vendor ?? "",
    type: (o.obligation_type ?? "sla") as string,
    owner: o.owner ?? "",
    assignee: o.assignee ?? "",
    dueDate: o.due_date ?? "",
    completedDate: o.completed_date ?? undefined,
    status: (o.status ?? "pending") as string,
    riskLevel: (o.risk_level ?? "info") as string,
    riskScore: o.risk_score ?? 0,
    slaStatus: (o.sla_status ?? "not_applicable") as string,
    slaRemaining: o.sla_remaining_hours ?? 0,
    financialImpact: o.financial_impact ?? 0,
    currency: o.currency ?? "USD",
    escalationLevel: o.escalation_level ?? 0,
    clauseReference: o.clause_reference ?? "",
    department: o.department ?? "",
    businessUnit: o.business_unit ?? "",
    geography: o.geography ?? "",
    description: o.description ?? "",
    isFavorite: o.is_favorite ?? false,
    completedBy: o.completed_by ?? undefined,
    completionNotes: o.completion_notes ?? undefined,
    createdAt: o.created_at ?? "",
    updatedAt: o.updated_at ?? "",
  };
}

export default function ObligationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const obligationId = params.obligationId as string;
  const [tab, setTab] = useState<TabId>("overview");
  const [editMode, setEditMode] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [pendingStatus, setPendingStatus] = useState<string | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [showStatusReason, setShowStatusReason] = useState(false);

  const { data: obligation, isLoading, error } = useQuery({
    queryKey: ["obligations", obligationId],
    queryFn: () => obligationsService.getObligation(obligationId),
    enabled: !!obligationId,
  });

  // ── Mutations ──
  const statusMut = useMutation({
    mutationFn: ({ id, status, reason }: { id: string; status: string; reason?: string }) => {
      const payload: Record<string, unknown> = { status };
      if (reason?.trim()) payload.notes = reason.trim();
      return obligationsService.updateObligation(id, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obligations", obligationId] });
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      queryClient.invalidateQueries({ queryKey: ["obligation-audit"] });
      setShowStatusReason(false);
      setStatusReason("");
      setPendingStatus(null);
    },
  });

  const completeMut = useMutation({
    mutationFn: (id: string) => obligationsService.completeObligation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obligations", obligationId] });
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      setActionLoading(null);
    },
    onError: () => setActionLoading(null),
  });

  const archiveMut = useMutation({
    mutationFn: (id: string) => obligationsService.archiveObligation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obligations", obligationId] });
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      setActionLoading(null);
    },
    onError: () => setActionLoading(null),
  });

  const statusOptions = [
    { value: "pending", label: "Pending", color: "text-yellow-700 bg-yellow-50" },
    { value: "in_progress", label: "In Progress", color: "text-blue-700 bg-blue-50" },
    { value: "pending_supplier", label: "Pending Supplier", color: "text-purple-700 bg-purple-50" },
    { value: "completed", label: "Completed", color: "text-green-700 bg-green-50" },
    { value: "cancelled", label: "Cancelled", color: "text-gray-600 bg-gray-100" },
    { value: "waived", label: "Waived", color: "text-gray-600 bg-gray-100" },
  ];

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-navy-500" />
          <p className="text-sm text-gray-500">Loading obligation...</p>
        </div>
      </div>
    );
  }

  if (error || !obligation) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center max-w-md">
          <ClipboardCheck className="w-12 h-12 text-gray-300" />
          <h2 className="text-lg font-semibold text-navy-900">Obligation not found</h2>
          <p className="text-sm text-gray-500">The obligation you're looking for doesn't exist or you don't have access.</p>
          <button onClick={() => router.push("/obligations")}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-600 text-white hover:bg-navy-700 transition-colors">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Obligations
          </button>
        </div>
      </div>
    );
  }

  const record = toObligationRecord(obligation);
  const sc = STATUS_CONFIG[record.status] || STATUS_CONFIG.pending;

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Sticky header */}
      <div className="sticky top-0 z-10 flex items-center gap-3 px-6 py-3 bg-white border-b border-gray-200 shadow-sm">
        <button onClick={() => router.back()} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors" title="Go back">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center">
          <ClipboardCheck className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-navy-900 truncate">{record.name}</h1>
          <p className="text-[11px] text-gray-500 truncate">{record.obligationNumber || record.id.slice(0, 8)} • {record.vendor}</p>
        </div>
        <div className="flex items-center gap-1.5">
          {/* Status badge */}
          <span className={`text-[10px] font-medium px-2 py-1 rounded-full ${sc.bg} ${sc.color}`}>{sc.label}</span>

          {/* Status change dropdown */}
          <select
            value=""
            onChange={(e) => { if (e.target.value) { setPendingStatus(e.target.value); setShowStatusReason(true); } }}
            className="text-[10px] px-2 py-1 border border-gray-200 rounded-lg bg-white text-gray-700 focus:border-navy-400"
          >
            <option value="">Change Status</option>
            {statusOptions.filter(s => s.value !== record.status).map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>

          {/* Action buttons */}
          {record.status !== "completed" && record.status !== "cancelled" && record.status !== "archived" && (
            <button onClick={() => { setActionLoading("complete"); completeMut.mutate(record.id); }} disabled={actionLoading === "complete"}
              className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded bg-green-100 text-green-700 hover:bg-green-200 disabled:opacity-50 transition-colors">
              {actionLoading === "complete" ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
              Complete
            </button>
          )}
          {record.status !== "archived" && (
            <button onClick={() => { setActionLoading("archive"); archiveMut.mutate(record.id); }} disabled={actionLoading === "archive"}
              className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-50 transition-colors">
              {actionLoading === "archive" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Archive className="w-3 h-3" />}
              Archive
            </button>
          )}
          <button onClick={() => setEditMode(!editMode)}
            className={`flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded transition-colors ${editMode ? "bg-navy-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {editMode ? <Eye className="w-3 h-3" /> : <Edit3 className="w-3 h-3" />}
            {editMode ? "View" : "Edit"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6 py-2 flex gap-1">
        <TabBtn label="Overview" icon={<FileText className="w-3 h-3" />} active={tab === "overview"} onClick={() => setTab("overview")} />
        <TabBtn label="SLA" icon={<Clock className="w-3 h-3" />} active={tab === "sla"} onClick={() => setTab("sla")} />
        <TabBtn label="Financial" icon={<DollarSign className="w-3 h-3" />} active={tab === "financial"} onClick={() => setTab("financial")} />
        <TabBtn label="Compliance" icon={<Shield className="w-3 h-3" />} active={tab === "compliance"} onClick={() => setTab("compliance")} />
        <TabBtn label="AI" icon={<Brain className="w-3 h-3" />} active={tab === "ai"} onClick={() => setTab("ai")} />
        <TabBtn label="Activity" icon={<Activity className="w-3 h-3" />} active={tab === "activity"} onClick={() => setTab("activity")} />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
        {tab === "overview" && (
          editMode ? (
            <EditForm record={record} obligationId={obligationId} onCancel={() => setEditMode(false)} />
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-6">
              <div className="flex items-center gap-4 flex-wrap">
                <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-full ${sc.bg} ${sc.color}`}>
                  {sc.label}
                </span>
                <span className="text-[11px] text-gray-500">Type: {OBLIGATION_TYPES.find(t => t.id === record.type)?.label || record.type}</span>
                <span className="text-[11px] text-gray-500">Vendor: {record.vendor}</span>
                <span className="text-[11px] text-gray-500">Due: {record.dueDate ? new Date(record.dueDate).toLocaleDateString() : "—"}</span>
              </div>
              {record.description && (
                <div>
                  <h3 className="text-xs font-semibold text-navy-900 mb-1.5">Description</h3>
                  <p className="text-[12px] text-gray-700 leading-relaxed">{record.description}</p>
                </div>
              )}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <DetailField label="Owner" value={record.owner} />
                <DetailField label="Assignee" value={record.assignee} />
                <DetailField label="Department" value={record.department} />
                <DetailField label="Business Unit" value={record.businessUnit} />
                <DetailField label="Geography" value={record.geography} />
                <DetailField label="Clause Reference" value={record.clauseReference} />
                <DetailField label="Risk Score" value={record.riskScore ? `${record.riskScore}/10` : "—"} />
                <DetailField label="Financial Impact" value={record.financialImpact ? `${record.currency} ${record.financialImpact.toLocaleString()}` : "—"} />
                <DetailField label="SLA Status" value={record.slaStatus.replace(/_/g, " ")} />
              </div>
            </div>
          )
        )}
        {tab === "sla" && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <p className="text-sm text-gray-500">SLA details for this obligation.</p>
          </div>
        )}
        {tab === "financial" && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <p className="text-sm text-gray-500">Financial impact details for this obligation.</p>
          </div>
        )}
        {tab === "compliance" && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <p className="text-sm text-gray-500">Compliance information for this obligation.</p>
          </div>
        )}
        {tab === "ai" && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <p className="text-sm text-gray-500">AI insights for this obligation.</p>
          </div>
        )}
        {tab === "activity" && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <ActivityTab obligationId={obligationId} />
          </div>
        )}
      </div>

      {/* Status Reason Modal */}
      <StatusReasonModal
        show={showStatusReason}
        status={pendingStatus}
        statusOptions={statusOptions}
        onConfirm={(reason) => {
          if (pendingStatus) {
            statusMut.mutate({ id: record.id, status: pendingStatus, reason });
          }
        }}
        onCancel={() => { setShowStatusReason(false); setPendingStatus(null); setStatusReason(""); }}
      />
    </div>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-[12px] text-gray-800 mt-0.5">{value || "—"}</p>
    </div>
  );
}

function EditForm({ record, obligationId, onCancel }: { record: ReturnType<typeof toObligationRecord>; obligationId: string; onCancel: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(record.name);
  const [description, setDescription] = useState(record.description);
  const [owner, setOwner] = useState(record.owner);
  const [assignee, setAssignee] = useState(record.assignee);
  const [dueDate, setDueDate] = useState(record.dueDate);
  const [department, setDepartment] = useState(record.department);
  const [businessUnit, setBusinessUnit] = useState(record.businessUnit);
  const [geography, setGeography] = useState(record.geography);
  const [clauseReference, setClauseReference] = useState(record.clauseReference);
  const [financialImpact, setFinancialImpact] = useState(String(record.financialImpact));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await obligationsService.updateObligation(obligationId, {
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
      queryClient.invalidateQueries({ queryKey: ["obligations", obligationId] });
      queryClient.invalidateQueries({ queryKey: ["obligations"] });
      onCancel();
    } catch (err) {
      console.error("Failed to save obligation:", err);
    } finally {
      setSaving(false);
    }
  };

  const inputClass = "w-full px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400 bg-white";

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
      <h3 className="text-sm font-semibold text-navy-900">Edit Obligation</h3>
      <div>
        <label className="text-[10px] font-semibold text-gray-600">Name</label>
        <input type="text" value={name} onChange={e => setName(e.target.value)} className={inputClass} />
      </div>
      <div>
        <label className="text-[10px] font-semibold text-gray-600">Description</label>
        <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} className={inputClass} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
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
        <button onClick={onCancel} className="px-3 py-1.5 text-[10px] font-medium text-gray-600 hover:text-gray-800">Cancel</button>
        <button onClick={handleSave} disabled={saving}
          className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-navy-600 text-white hover:bg-navy-700 disabled:opacity-50 inline-flex items-center gap-1">
          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
          Save Changes
        </button>
      </div>
    </div>
  );
}

// ── Status Reason Modal ─────────────────────────────────────────

function StatusReasonModal({
  show, status, statusOptions, onConfirm, onCancel,
}: {
  show: boolean; status: string | null; statusOptions: { value: string; label: string }[];
  onConfirm: (reason: string) => void; onCancel: () => void;
}) {
  const [reason, setReason] = useState("");
  if (!show || !status) return null;
  const label = statusOptions.find(o => o.value === status)?.label || status;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onCancel}>
      <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-sm mx-4 p-5" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-navy-900">Change Status</h3>
        <p className="text-[11px] text-gray-500 mt-1">Reason for changing to <span className="font-medium text-navy-700">{label}</span></p>
        <div className="mt-3">
          <label className="text-[10px] font-semibold text-gray-600">Reason <span className="text-red-500">*</span></label>
          <textarea value={reason} onChange={e => setReason(e.target.value)}
            placeholder="Enter the reason for this status change..."
            rows={3} className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400 resize-none" autoFocus />
          {reason.trim().length > 0 && reason.trim().length < 5 && (
            <p className="text-[9px] text-red-500 mt-0.5">Please enter at least 5 characters</p>
          )}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-1.5 text-[10px] font-medium text-gray-600 hover:text-gray-800 rounded-lg hover:bg-gray-50 transition-colors">Cancel</button>
          <button onClick={() => { if (reason.trim().length >= 5) { onConfirm(reason.trim()); setReason(""); } }}
            disabled={reason.trim().length < 5}
            className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-navy-600 text-white hover:bg-navy-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

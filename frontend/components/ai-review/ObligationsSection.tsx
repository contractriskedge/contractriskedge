/**
 * ObligationsSection — view and manage AI-extracted obligations within the Review Workspace.
 *
 * Features:
 * - View obligations linked to the current contract/review
 * - See obligation name, type, due date, priority, status, source clause
 * - Create new obligation
 * - Edit existing obligation
 * - Delete obligation
 * - Link obligation to source clause
 * - Read-only after contract approval
 */

"use client";

import React, { useState, useMemo, useCallback } from "react";
import { useQueryClient, useMutation, useQuery } from "@tanstack/react-query";
import {
  ClipboardCheck, Plus, Edit3, Trash2, ExternalLink, Loader2,
  AlertCircle, FileText, Calendar, User, Shield, DollarSign,
  CheckCircle2, XCircle, Clock, AlertTriangle, Link2,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";
import { obligationsService } from "@/services/api/obligations";
import type { ObligationResponse, ObligationCreateRequest, ObligationUpdateRequest } from "@/services/api/obligations";
import { isReviewDecisionLocked } from "./reviewDecision";
import { useObligationsByContract } from "./hooks";

// ── Helpers ──────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string; icon: React.ElementType }> = {
  draft: { color: "text-gray-600", bg: "bg-gray-100", label: "Draft", icon: FileText },
  pending: { color: "text-yellow-700", bg: "bg-yellow-50", label: "Pending", icon: Clock },
  open: { color: "text-blue-700", bg: "bg-blue-50", label: "Open", icon: AlertCircle },
  in_progress: { color: "text-blue-700", bg: "bg-blue-50", label: "In Progress", icon: Clock },
  pending_supplier: { color: "text-purple-700", bg: "bg-purple-50", label: "Pending Supplier", icon: Clock },
  completed: { color: "text-green-700", bg: "bg-green-50", label: "Completed", icon: CheckCircle2 },
  overdue: { color: "text-red-700", bg: "bg-red-50", label: "Overdue", icon: AlertTriangle },
  cancelled: { color: "text-gray-500", bg: "bg-gray-100", label: "Cancelled", icon: XCircle },
  archived: { color: "text-gray-400", bg: "bg-gray-50", label: "Archived", icon: ArchiveIcon },
  waived: { color: "text-gray-500", bg: "bg-gray-100", label: "Waived", icon: XCircle },
};

function ArchiveIcon({ className }: { className?: string }) {
  return <XCircle className={className} />;
}

const OBLIGATION_TYPES: Record<string, string> = {
  payment: "Payment", renewal: "Renewal", notice: "Notice",
  insurance: "Insurance", audit_rights: "Audit Rights",
  data_retention: "Data Retention", data_deletion: "Data Deletion",
};

const PRIORITY_LEVELS: Record<string, string> = {
  critical: "Critical", high: "High", medium: "Medium", low: "Low",
};

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch { return "—"; }
}

// ── Component ────────────────────────────────────────────────────

export function ObligationsSection() {
  const ctx = useReviewContext();
  const { selectedReviewId, selectedReview, workflow } = ctx;
  const queryClient = useQueryClient();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingObligation, setEditingObligation] = useState<ObligationResponse | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const isLocked = selectedReview ? isReviewDecisionLocked(selectedReview, workflow) : false;

  // Fetch obligations for this contract/review
  const { data: obligationsData, isLoading, refetch } = useObligationsByContract(selectedReviewId ?? undefined);
  const obligations: ObligationResponse[] = obligationsData?.obligations ?? [];

  // ── Mutations ──────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (body: ObligationCreateRequest) => obligationsService.createObligation(body),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["obligations"] }); refetch(); showToast("Obligation created"); },
    onError: (err: Error) => showToast(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: ObligationUpdateRequest }) => obligationsService.updateObligation(id, body),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["obligations"] }); refetch(); showToast("Obligation updated"); },
    onError: (err: Error) => showToast(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => obligationsService.deleteObligation(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["obligations"] }); refetch(); showToast("Obligation deleted"); },
    onError: (err: Error) => showToast(err.message),
  });

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleCreate = useCallback(async (data: ObligationCreateRequest) => {
    await createMutation.mutateAsync(data);
    setShowCreateModal(false);
  }, [createMutation]);

  const handleUpdate = useCallback(async (id: string, data: ObligationUpdateRequest) => {
    await updateMutation.mutateAsync({ id, body: data });
    setEditingObligation(null);
  }, [updateMutation]);

  const handleDelete = useCallback(async (id: string) => {
    await deleteMutation.mutateAsync(id);
    setDeleteConfirm(null);
  }, [deleteMutation]);

  if (!selectedReviewId) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <ClipboardCheck className="w-10 h-10 text-gray-300 mb-3" />
        <p className="text-sm font-medium text-gray-500">Select a review to view obligations</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 text-navy-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Obligations</h3>
          <p className="text-[10px] text-gray-500 mt-0.5">
            {obligations.length} obligation{obligations.length !== 1 ? "s" : ""} linked to this contract
            {isLocked && <span className="ml-1 text-amber-600">· Read-only (approved)</span>}
          </p>
        </div>
        {!isLocked && (
          <button onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors">
            <Plus className="w-3.5 h-3.5" /> New Obligation
          </button>
        )}
      </div>

      {/* Empty State */}
      {obligations.length === 0 && (
        <div className="flex flex-col items-center py-12 text-center border-2 border-dashed border-gray-200 rounded-xl">
          <ClipboardCheck className="w-8 h-8 text-gray-300 mb-2" />
          <p className="text-xs font-medium text-gray-500">No obligations extracted for this contract</p>
          <p className="text-[10px] text-gray-400 mt-1">AI-extracted obligations will appear here after analysis</p>
          {!isLocked && (
            <button onClick={() => setShowCreateModal(true)}
              className="mt-3 flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors">
              <Plus className="w-3 h-3" /> Create First Obligation
            </button>
          )}
        </div>
      )}

      {/* Obligations List */}
      {obligations.length > 0 && (
        <div className="space-y-2">
          {obligations.map((ob) => {
            const sc = STATUS_CONFIG[ob.status] || STATUS_CONFIG.pending;
            const StatusIcon = sc.icon;
            const isEditing = editingObligation?.id === ob.id;
            return (
              <div key={ob.id}
                className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg overflow-hidden hover:border-gray-300 dark:hover:border-navy-600 transition-colors">
                {/* Main Row */}
                <div className="flex items-center justify-between px-3 py-2.5">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    {/* Status Icon */}
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${sc.bg}`}>
                      <StatusIcon className={`w-3.5 h-3.5 ${sc.color}`} />
                    </div>
                    {/* Info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold text-navy-900 dark:text-white truncate">{ob.name}</span>
                        <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${sc.bg} ${sc.color}`}>{sc.label}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-[9px] text-gray-500 flex-wrap">
                        <span>{OBLIGATION_TYPES[ob.obligation_type] || ob.obligation_type}</span>
                        {ob.due_date && <><span className="w-1 h-1 rounded-full bg-gray-300" /><span>Due: {fmtDate(ob.due_date)}</span></>}
                        {ob.risk_score > 0 && <><span className="w-1 h-1 rounded-full bg-gray-300" /><span>Risk: {ob.risk_score}/10</span></>}
                        {ob.clause_reference && (
                          <><span className="w-1 h-1 rounded-full bg-gray-300" />
                            <span className="inline-flex items-center gap-0.5 text-blue-600">
                              <Link2 className="w-2.5 h-2.5" /> {ob.clause_reference}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  {/* Actions */}
                  {!isLocked && (
                    <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                      <button onClick={() => setEditingObligation(ob)}
                        className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-navy-700 transition-colors" title="Edit">
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => setDeleteConfirm(ob.id)}
                        className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600 transition-colors" title="Delete">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Inline Edit Form */}
                {isEditing && (
                  <ObligationEditForm
                    obligation={ob}
                    onSave={(data) => handleUpdate(ob.id, data)}
                    onCancel={() => setEditingObligation(null)}
                    isSaving={updateMutation.isPending}
                  />
                )}

                {/* Delete Confirmation */}
                {deleteConfirm === ob.id && (
                  <div className="px-3 py-2 bg-red-50 border-t border-red-200 flex items-center justify-between">
                    <span className="text-[10px] text-red-700">Delete "{ob.name}"? This cannot be undone.</span>
                    <div className="flex items-center gap-1.5">
                      <button onClick={() => setDeleteConfirm(null)}
                        className="px-2 py-1 text-[9px] font-medium rounded bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
                      <button onClick={() => handleDelete(ob.id)}
                        className="px-2 py-1 text-[9px] font-medium rounded bg-red-600 text-white hover:bg-red-700">Delete</button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <ObligationCreateModal
          contractId={selectedReviewId}
          contractName={selectedReview?.contract_name}
          onSave={handleCreate}
          onCancel={() => setShowCreateModal(false)}
          isSaving={createMutation.isPending}
        />
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 px-3 py-2 rounded-lg bg-navy-800 text-white text-[10px] font-medium shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

// ── Inline Edit Form ─────────────────────────────────────────────

function ObligationEditForm({ obligation, onSave, onCancel, isSaving }: {
  obligation: ObligationResponse;
  onSave: (data: ObligationUpdateRequest) => void;
  onCancel: () => void;
  isSaving: boolean;
}) {
  const [name, setName] = useState(obligation.name);
  const [description, setDescription] = useState(obligation.description || "");
  const [dueDate, setDueDate] = useState(obligation.due_date ? obligation.due_date.slice(0, 10) : "");
  const [notes, setNotes] = useState(obligation.notes || "");
  const [clauseReference, setClauseReference] = useState(obligation.clause_reference || "");

  const handleSave = () => {
    if (!name.trim()) return;
    onSave({
      name: name.trim(),
      description: description.trim() || undefined,
      dueDate: dueDate ? new Date(dueDate).toISOString() : undefined,
      notes: notes.trim() || undefined,
      clauseReference: clauseReference.trim() || undefined,
    });
  };

  return (
    <div className="px-3 py-2.5 bg-gray-50 border-t border-gray-200 space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[8px] font-semibold text-gray-500 uppercase">Name</label>
          <input value={name} onChange={e => setName(e.target.value)}
            className="w-full mt-0.5 px-2 py-1 text-[10px] border border-gray-200 rounded focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
        </div>
        <div>
          <label className="text-[8px] font-semibold text-gray-500 uppercase">Due Date</label>
          <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)}
            className="w-full mt-0.5 px-2 py-1 text-[10px] border border-gray-200 rounded focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
        </div>
        <div className="col-span-2">
          <label className="text-[8px] font-semibold text-gray-500 uppercase">Description</label>
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
            className="w-full mt-0.5 px-2 py-1 text-[10px] border border-gray-200 rounded focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
        </div>
        <div className="col-span-2">
          <label className="text-[8px] font-semibold text-gray-500 uppercase">Clause Reference</label>
          <input value={clauseReference} onChange={e => setClauseReference(e.target.value)}
            placeholder="e.g. Section 5.3 - Indemnification"
            className="w-full mt-0.5 px-2 py-1 text-[10px] border border-gray-200 rounded focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
        </div>
        <div className="col-span-2">
          <label className="text-[8px] font-semibold text-gray-500 uppercase">Notes</label>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
            className="w-full mt-0.5 px-2 py-1 text-[10px] border border-gray-200 rounded focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
        </div>
      </div>
      <div className="flex justify-end gap-1.5 pt-1">
        <button onClick={onCancel} className="px-2 py-1 text-[9px] font-medium rounded bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
        <button onClick={handleSave} disabled={isSaving || !name.trim()}
          className="px-2 py-1 text-[9px] font-medium rounded bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50">
          {isSaving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}

// ── Create Modal ─────────────────────────────────────────────────

function ObligationCreateModal({ contractId, contractName, onSave, onCancel, isSaving }: {
  contractId: string;
  contractName?: string;
  onSave: (data: ObligationCreateRequest) => void;
  onCancel: () => void;
  isSaving: boolean;
}) {
  const [name, setName] = useState("");
  const [obligationType, setObligationType] = useState("payment");
  const [dueDate, setDueDate] = useState("");
  const [description, setDescription] = useState("");
  const [notes, setNotes] = useState("");
  const [clauseReference, setClauseReference] = useState("");

  const handleSave = () => {
    if (!name.trim()) return;
    onSave({
      name: name.trim(),
      obligationType,
      description: description.trim() || undefined,
      dueDate: dueDate ? new Date(dueDate).toISOString() : undefined,
      notes: notes.trim() || undefined,
      clauseReference: clauseReference.trim() || undefined,
      contractUuidId: contractId,
      contractName: contractName,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onCancel}>
      <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-navy-900">New Obligation</h3>
          <p className="text-[10px] text-gray-500 mt-0.5">Create a new obligation for this contract</p>
        </div>
        <div className="p-4 space-y-3">
          <div>
            <label className="text-[10px] font-semibold text-gray-600">Name <span className="text-red-500">*</span></label>
            <input value={name} onChange={e => setName(e.target.value)}
              className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-gray-600">Type</label>
            <select value={obligationType} onChange={e => setObligationType(e.target.value)}
              className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400">
              {Object.entries(OBLIGATION_TYPES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] font-semibold text-gray-600">Due Date</label>
            <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)}
              className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-gray-600">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
              className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-gray-600">Clause Reference</label>
            <input value={clauseReference} onChange={e => setClauseReference(e.target.value)}
              placeholder="e.g. Section 5.3 - Indemnification"
              className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-gray-600">Notes</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
              className="w-full mt-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400" />
          </div>
        </div>
        <div className="px-4 py-3 border-t border-gray-100 flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
          <button onClick={handleSave} disabled={isSaving || !name.trim()}
            className="px-3 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50">
            {isSaving ? "Creating..." : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

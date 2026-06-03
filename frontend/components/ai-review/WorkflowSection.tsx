/**
 * WorkflowSection — SLA prioritization, queue aging, escalation, workload balancing.
 *
 * Shows:
 * - Visual workflow stage progression
 * - SLA timer with color-coded status
 * - Queue aging indicators
 * - Escalation level
 * - Reviewer workload balancing
 * - Stage transition actions
 * - Queue position and metrics
 */

"use client";

import React, { useState, useEffect } from "react";
import {
  Workflow, CheckCircle2, Clock, AlertTriangle, User,
  ArrowRight, Send, XCircle, SkipForward, ShieldAlert,
  BarChart3, TrendingUp, Users, ChevronDown, X, MessageSquare, Calendar, CheckCircle,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";
import { useReviewerWorkloads, useQueueMetrics, useAdvanceWorkflow } from "./hooks";
import { reviewService } from "@/services/api/reviews";

export function WorkflowSection() {
  const ctx = useReviewContext();
  const { workflow, selectedReview, selectedReviewId } = ctx;
  const { data: reviewers } = useReviewerWorkloads();
  const { data: metrics } = useQueueMetrics();
  const advanceMutation = useAdvanceWorkflow();

  const [showActions, setShowActions] = useState(false);
  const [advanceModal, setAdvanceModal] = useState<{ action: string } | null>(null);
  const [advanceAssignee, setAdvanceAssignee] = useState("");
  const [advanceNote, setAdvanceNote] = useState("");
  const [reassignModal, setReassignModal] = useState(false);
  const [reassignTarget, setReassignTarget] = useState("");
  const [dueDateModal, setDueDateModal] = useState(false);
  const [dueDateValue, setDueDateValue] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "info" } | null>(null);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const showToast = (message: string, type: "success" | "info" = "success") => {
    setToast({ message, type });
  };

  const handleAdvance = async () => {
    if (!selectedReviewId || !advanceModal) return;
    await advanceMutation.mutateAsync({
      reviewId: selectedReviewId,
      action: advanceModal.action,
      assignee_id: advanceAssignee || undefined,
      note: advanceNote || undefined,
    });
    const queueName = advanceModal.action.replace(/_/g, " ");
    const assigneeMsg = advanceAssignee ? ` → assigned to ${advanceAssignee}` : "";
    showToast(`Moved to ${queueName}${assigneeMsg}`);
    setAdvanceModal(null);
    setAdvanceAssignee("");
    setAdvanceNote("");
  };

  const handleReassign = async () => {
    if (!selectedReviewId || !reassignTarget) return;
    try {
      await reviewService.assign(selectedReviewId, { assignee_id: reassignTarget, role: "reviewer" });
      showToast(`Reassigned to ${reassignTarget}`);
      setReassignModal(false);
      setReassignTarget("");
    } catch { /* handled by UI */ }
  };

  const handleSetDueDate = async () => {
    if (!selectedReviewId || !dueDateValue) return;
    try {
      await reviewService.assign(selectedReviewId, { assignee_id: "", role: "reviewer", due_date: dueDateValue });
      const d = new Date(dueDateValue).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
      showToast(`Due date set to ${d}`);
      setDueDateModal(false);
      setDueDateValue("");
    } catch { /* handled by UI */ }
  };

  if (!workflow || !selectedReview) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <Workflow className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-xs text-gray-500">Workflow data unavailable</p>
        </div>
      </div>
    );
  }

  const stageStyles: Record<string, { bg: string; dot: string; text: string }> = {
    completed: { bg: "bg-green-100 dark:bg-green-900/20", dot: "bg-green-500", text: "text-green-700 dark:text-green-300" },
    current: { bg: "bg-blue-100 dark:bg-blue-900/20", dot: "bg-blue-500", text: "text-blue-700 dark:text-blue-300" },
    pending: { bg: "bg-gray-100 dark:bg-gray-800", dot: "bg-gray-400", text: "text-gray-500" },
    skipped: { bg: "bg-gray-100 dark:bg-gray-800", dot: "bg-gray-300", text: "text-gray-400" },
    rejected: { bg: "bg-red-100 dark:bg-red-900/20", dot: "bg-red-500", text: "text-red-700" },
  };

  return (
    <div className="p-4 space-y-4">
      {/* ── SLA & Queue Health ──────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <Clock className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">SLA Status</span>
          </div>
          <div className={`px-2 py-1.5 rounded text-[11px] font-medium ${
            selectedReview.sla_status === "critical_overdue" ? "bg-red-100 text-red-700" :
            selectedReview.sla_status === "overdue" ? "bg-red-50 text-red-600" :
            selectedReview.sla_status === "warning" ? "bg-amber-100 text-amber-700" :
            "bg-green-100 text-green-700"
          }`}>
            <div className="flex items-center justify-between">
              <span className="capitalize font-semibold">{selectedReview.sla_status.replace(/_/g, " ")}</span>
              <span>{workflow.sla_remaining_hours > 0 ? `${Math.floor(workflow.sla_remaining_hours)}h remaining` : `${Math.floor(Math.abs(workflow.sla_remaining_hours))}h overdue`}</span>
            </div>
          </div>
          <div className="mt-2 space-y-1 text-[9px]">
            <div className="flex justify-between"><span className="text-gray-400">Queue Position</span><span className="font-medium">{workflow.queue_position} of {workflow.queue_total}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Age in Queue</span><span className={`font-medium ${selectedReview.age_hours > 72 ? "text-red-600" : selectedReview.age_hours > 48 ? "text-amber-600" : ""}`}>{Math.round(selectedReview.age_hours)}h</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Escalation</span><span className={`font-medium ${workflow.escalation_level > 0 ? "text-red-600" : ""}`}>{workflow.escalation_level > 0 ? `Level ${workflow.escalation_level}` : "None"}</span></div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <BarChart3 className="w-3.5 h-3.5 text-purple-500" />
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Queue Metrics</span>
          </div>
          {metrics && (
            <div className="space-y-1 text-[9px]">
              <div className="flex justify-between"><span className="text-gray-400">Total in Queue</span><span className="font-medium">{metrics.total}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Unassigned in Queue</span><span className="font-medium text-amber-600">{metrics.unassigned}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Overdue</span><span className="font-medium text-red-600">{metrics.overdue + metrics.critical_overdue}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">SLA at Risk</span><span className="font-medium text-amber-600">{metrics.sla_at_risk}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Completed Today</span><span className="font-medium text-green-600">{metrics.completed_today}</span></div>
            </div>
          )}
        </div>
      </div>

      {/* ── Ownership & Approver Panel ──────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <User className="w-3.5 h-3.5 text-indigo-500" />
          <span className="text-[9px] font-semibold text-gray-500 uppercase">Review Ownership</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {/* Current Owner */}
          <div className="p-2 rounded bg-gray-50 dark:bg-navy-750">
            <span className="text-[7px] font-semibold text-gray-500 uppercase">Current Owner</span>
            <div className="flex items-center gap-1.5 mt-1">
              {selectedReview.assigned_to_name ? (
                <>
                  <div className="w-6 h-6 rounded-full bg-navy-200 dark:bg-navy-600 flex items-center justify-center text-[8px] font-bold text-navy-700 flex-shrink-0">
                    {selectedReview.assigned_to_name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                  </div>
                  <div>
                    <p className="text-[10px] font-medium text-navy-900 dark:text-white">{selectedReview.assigned_to_name}</p>
                    <p className="text-[7px] text-gray-400">{workflow.reviewers.find(r => r.user_id === selectedReview.assigned_to)?.role || "—"}</p>
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-1.5 text-amber-600">
                  <AlertTriangle className="w-3 h-3" />
                  <p className="text-[10px] font-medium">Awaiting assignment — stage: {workflow.current_stage.replace(/_/g, " ")}</p>
                </div>
              )}
            </div>
          </div>

          {/* Next Approver */}
          <div className="p-2 rounded bg-gray-50 dark:bg-navy-750">
            <span className="text-[7px] font-semibold text-gray-500 uppercase">Next Approver</span>
            <div className="flex items-center gap-1.5 mt-1">
              <div className="w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center text-[8px] font-bold text-amber-700 flex-shrink-0">
                {workflow.stages.find(s => s.status === "current")?.label.slice(0, 2).toUpperCase() || "—"}
              </div>
              <div>
                <p className="text-[10px] font-medium text-amber-700 dark:text-amber-300">
                  {workflow.stages.find(s => s.status === "current")?.label || "—"}
                </p>
                <p className="text-[7px] text-gray-400">
                  {workflow.sla_remaining_hours > 0
                    ? `${Math.floor(workflow.sla_remaining_hours)}h remaining`
                    : `${Math.floor(Math.abs(workflow.sla_remaining_hours))}h overdue`}
                </p>
              </div>
            </div>
          </div>

          {/* Days Remaining */}
          <div className="p-2 rounded bg-gray-50 dark:bg-navy-750">
            <span className="text-[7px] font-semibold text-gray-500 uppercase">Days Remaining</span>
            <p className={`text-sm font-bold mt-1 ${
              selectedReview.sla_status === "critical_overdue" ? "text-red-600" :
              selectedReview.sla_status === "overdue" ? "text-red-500" :
              selectedReview.sla_status === "warning" ? "text-amber-600" : "text-green-600"
            }`}>
              {workflow.sla_remaining_hours > 0
                ? `${Math.ceil(workflow.sla_remaining_hours / 24)}d`
                : "Overdue"}
            </p>
          </div>

          {/* Escalation Threshold */}
          <div className="p-2 rounded bg-gray-50 dark:bg-navy-750">
            <span className="text-[7px] font-semibold text-gray-500 uppercase">Escalation Threshold</span>
            <p className={`text-sm font-bold mt-1 ${workflow.escalation_level > 0 ? "text-red-600" : "text-gray-500"}`}>
              {workflow.escalation_level > 0
                ? `Level ${workflow.escalation_level}`
                : workflow.sla_remaining_hours < 6
                  ? "Imminent"
                  : "Normal"}
            </p>
          </div>
        </div>
      </div>

      {/* ── Workflow Stages ──────────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-3">
          <Workflow className="w-3.5 h-3.5 text-navy-500" />
          <span className="text-[9px] font-semibold text-gray-500 uppercase">Workflow Stages</span>
        </div>
        <div className="flex items-center gap-1">
          {workflow.stages.map((stage, index) => {
            const style = stageStyles[stage.status] || stageStyles.pending;
            const isLast = index === workflow.stages.length - 1;
            return (
              <React.Fragment key={stage.id}>
                <div className="flex flex-col items-center">
                  <div className={`w-7 h-7 rounded-full ${style.bg} flex items-center justify-center`}>
                    {stage.status === "completed" ? <CheckCircle2 className={`w-3.5 h-3.5 ${style.text}`} /> :
                     stage.status === "current" ? <ArrowRight className={`w-3.5 h-3.5 ${style.text}`} /> :
                     stage.status === "rejected" ? <XCircle className={`w-3.5 h-3.5 ${style.text}`} /> :
                     <div className={`w-2 h-2 rounded-full ${style.dot}`} />}
                  </div>
                  <span className={`text-[7px] mt-1 text-center max-w-[50px] truncate ${
                    stage.status === "current" ? "text-blue-700 font-semibold" : "text-gray-500"
                  }`}>{stage.label}</span>
                  {stage.completed_by && (
                    <span className="text-[5px] text-gray-400 mt-0.5">{stage.completed_by}</span>
                  )}
                </div>
                {!isLast && (
                  <div className={`flex-1 h-0.5 mx-0.5 ${stage.status === "completed" ? "bg-green-400" : stage.status === "current" ? "bg-blue-400" : "bg-gray-200 dark:bg-navy-700"}`} />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Approval Chain — Legal → Procurement → Security → Business → Final */}
        <div className="mt-3 pt-2 border-t border-gray-100 dark:border-navy-700">
          <span className="text-[7px] font-semibold text-gray-500 uppercase">Approval Chain</span>
          <div className="flex items-center gap-1 mt-1">
            {["Legal", "Procurement", "Security", "Business", "Final"].map((step, i) => {
              const stageMatch = workflow.stages.find(s => s.label.toLowerCase().includes(step.toLowerCase()));
              const isDone = stageMatch?.status === "completed";
              const isCurrent = stageMatch?.status === "current";
              return (
                <React.Fragment key={step}>
                  <div className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[7px] font-medium ${
                    isDone ? "bg-green-100 text-green-700" :
                    isCurrent ? "bg-blue-100 text-blue-700 ring-1 ring-blue-300" :
                    "bg-gray-100 text-gray-400"
                  }`}>
                    {isDone && <CheckCircle2 className="w-2 h-2" />}
                    {step}
                  </div>
                  {i < 4 && <ChevronDown className="w-2 h-2 -rotate-90 text-gray-300" />}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between">
          <span className="text-[9px] text-gray-500 capitalize">Current: <strong>{workflow.current_stage.replace(/_/g, " ")}</strong></span>
          {workflow.available_actions.length > 0 && (
            <div className="relative">
              <button onClick={() => setShowActions(!showActions)} className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-navy-600 text-white hover:bg-navy-700 transition-colors">
                Actions <Send className="w-2.5 h-2.5" />
              </button>
              {showActions && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowActions(false)} />
                  <div className="absolute right-0 top-full mt-1 z-20 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg shadow-lg py-1 w-44">
                    {workflow.available_actions.map(action => (
                      <button key={action} onClick={() => { setShowActions(false); setAdvanceModal({ action }); }}
                        className="w-full text-left px-3 py-1.5 text-[9px] text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700 flex items-center gap-1.5">
                        <Send className="w-2.5 h-2.5" /> {action.replace(/_/g, " ")}
                      </button>
                    ))}
                    <div className="border-t border-gray-100 dark:border-navy-700 my-1" />
                    <button onClick={() => { setShowActions(false); setReassignModal(true); }}
                      className="w-full text-left px-3 py-1.5 text-[9px] text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700 flex items-center gap-1.5">
                      <User className="w-2.5 h-2.5" /> Reassign
                    </button>
                    <button onClick={() => { setShowActions(false); setDueDateModal(true); }}
                      className="w-full text-left px-3 py-1.5 text-[9px] text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700 flex items-center gap-1.5">
                      <Clock className="w-2.5 h-2.5" /> Set Due Date
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Due Dates */}
        <div className="mt-2 pt-2 border-t border-gray-100 dark:border-navy-700 grid grid-cols-3 gap-2 text-[8px]">
          <div>
            <span className="text-gray-400">SLA Deadline</span>
            <p className={`font-medium mt-0.5 ${
              selectedReview.sla_status === "critical_overdue" ? "text-red-600" :
              selectedReview.sla_status === "overdue" ? "text-red-500" :
              selectedReview.sla_status === "warning" ? "text-amber-600" : "text-green-600"
            }`}>
              {workflow.sla_remaining_hours > 0
                ? `${Math.floor(workflow.sla_remaining_hours)}h remaining`
                : `${Math.floor(Math.abs(workflow.sla_remaining_hours))}h overdue`}
            </p>
          </div>
          <div>
            <span className="text-gray-400">Target Completion</span>
            <p className="font-medium text-navy-900 dark:text-white mt-0.5">
              {selectedReview.sla_deadline
                ? new Date(selectedReview.sla_deadline).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                : "—"}
            </p>
          </div>
          <div>
            <span className="text-gray-400">Escalation</span>
            <p className={`font-medium mt-0.5 ${workflow.escalation_level > 0 ? "text-red-600" : "text-gray-500"}`}>
              {workflow.escalation_level > 0 ? `Level ${workflow.escalation_level}` : "None"}
            </p>
          </div>
        </div>
      </div>

      {/* ── Advance Action Modal ──────────────────────────────────────────── */}
      {advanceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setAdvanceModal(null)}>
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl border border-gray-200 dark:border-navy-700 p-4 w-80 max-w-full mx-2" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-navy-900 dark:text-white capitalize">Send to {advanceModal.action.replace(/_/g, " ")}</h4>
              <button onClick={() => setAdvanceModal(null)} className="p-1 rounded hover:bg-gray-100"><X className="w-3.5 h-3.5" /></button>
            </div>
            <div className="space-y-2.5">
              <div>
                <label className="text-[9px] font-semibold text-gray-500 uppercase">Assignee</label>
                <select value={advanceAssignee} onChange={e => setAdvanceAssignee(e.target.value)}
                  className="w-full mt-0.5 px-2 py-1.5 text-[11px] border border-gray-200 rounded-lg bg-white dark:bg-navy-700 dark:border-navy-600">
                  <option value="">Auto-assign (no specific assignee)</option>
                  {reviewers?.map(r => (
                    <option key={r.user_id} value={r.user_id}>{r.name} ({r.active_reviews} active)</option>
                  ))}
                  <option value="legal@test.com">Legal Reviewer</option>
                  <option value="exec@test.com">Executive Reviewer</option>
                  <option value="compliance@test.com">Compliance Reviewer</option>
                </select>
              </div>
              <div>
                <label className="text-[9px] font-semibold text-gray-500 uppercase">Handoff Note</label>
                <textarea value={advanceNote} onChange={e => setAdvanceNote(e.target.value)}
                  placeholder="Reason for this transition..."
                  className="w-full mt-0.5 px-2 py-1.5 text-[11px] border border-gray-200 rounded-lg bg-white dark:bg-navy-700 dark:border-navy-600 resize-none"
                  rows={2} />
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={() => setAdvanceModal(null)}
                  className="flex-1 px-3 py-1.5 text-[10px] font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
                  Cancel
                </button>
                <button onClick={handleAdvance} disabled={advanceMutation.isPending}
                  className="flex-1 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50">
                  {advanceMutation.isPending ? "Advancing..." : "Advance"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Reassign Modal ────────────────────────────────────────────────── */}
      {reassignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setReassignModal(false)}>
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl border border-gray-200 dark:border-navy-700 p-4 w-72 max-w-full mx-2" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-navy-900 dark:text-white">Reassign Reviewer</h4>
              <button onClick={() => setReassignModal(false)} className="p-1 rounded hover:bg-gray-100"><X className="w-3.5 h-3.5" /></button>
            </div>
            <div className="space-y-2.5">
              <div>
                <label className="text-[9px] font-semibold text-gray-500 uppercase">New Assignee</label>
                <select value={reassignTarget} onChange={e => setReassignTarget(e.target.value)}
                  className="w-full mt-0.5 px-2 py-1.5 text-[11px] border border-gray-200 rounded-lg bg-white dark:bg-navy-700 dark:border-navy-600">
                  <option value="">Select reviewer...</option>
                  {reviewers?.map(r => (
                    <option key={r.user_id} value={r.user_id}>{r.name} ({r.active_reviews} active)</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={() => setReassignModal(false)}
                  className="flex-1 px-3 py-1.5 text-[10px] font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
                  Cancel
                </button>
                <button onClick={handleReassign} disabled={!reassignTarget}
                  className="flex-1 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50">
                  Reassign
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Set Due Date Modal ────────────────────────────────────────────── */}
      {dueDateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setDueDateModal(false)}>
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl border border-gray-200 dark:border-navy-700 p-4 w-72 max-w-full mx-2" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-navy-900 dark:text-white">Set Due Date</h4>
              <button onClick={() => setDueDateModal(false)} className="p-1 rounded hover:bg-gray-100"><X className="w-3.5 h-3.5" /></button>
            </div>
            <div className="space-y-2.5">
              <div>
                <label className="text-[9px] font-semibold text-gray-500 uppercase">Due Date</label>
                <input type="datetime-local" value={dueDateValue} onChange={e => setDueDateValue(e.target.value)}
                  className="w-full mt-0.5 px-2 py-1.5 text-[11px] border border-gray-200 rounded-lg bg-white dark:bg-navy-700 dark:border-navy-600" />
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={() => setDueDateModal(false)}
                  className="flex-1 px-3 py-1.5 text-[10px] font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
                  Cancel
                </button>
                <button onClick={handleSetDueDate} disabled={!dueDateValue}
                  className="flex-1 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50">
                  Set
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Reviewer Workload ────────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Users className="w-3.5 h-3.5 text-indigo-500" />
          <span className="text-[9px] font-semibold text-gray-500 uppercase">Reviewer Workload</span>
        </div>
        {reviewers && (
          <div className="space-y-1.5">
            {reviewers.sort((a, b) => b.workload_pct - a.workload_pct).map(r => (
              <div key={r.user_id} className="flex items-center gap-2 group">
                <div className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-700 flex items-center justify-center text-[7px] font-bold text-navy-600 flex-shrink-0">
                  {r.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-medium text-navy-900 dark:text-white">{r.name}</span>
                    <span className={`text-[8px] font-medium ${r.workload_pct > 70 ? "text-red-600" : r.workload_pct > 50 ? "text-amber-600" : "text-green-600"}`}>
                      {r.active_reviews} active
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <div className="flex-1 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${r.workload_pct > 70 ? "bg-red-500" : r.workload_pct > 50 ? "bg-amber-500" : "bg-green-500"}`}
                        style={{ width: `${r.workload_pct}%` }} />
                    </div>
                    <span className="text-[7px] text-gray-400">{r.workload_pct}%</span>
                    {r.sla_breaches > 0 && <AlertTriangle className="w-2.5 h-2.5 text-red-500" />}
                  </div>
                </div>
                {/* Reassign button — visible on hover */}
                <button className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 px-1.5 py-0.5 text-[7px] font-medium rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200">
                  <User className="w-2 h-2" /> Reassign
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Toast Notification ───────────────────────────────────────────── */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-slide-up">
          <div className={`flex items-center gap-2 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${
            toast.type === "success"
              ? "bg-green-50 border-green-200 text-green-800"
              : "bg-blue-50 border-blue-200 text-blue-800"
          }`}>
            {toast.type === "success" ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <Clock className="w-4 h-4 text-blue-500" />
            )}
            {toast.message}
          </div>
        </div>
      )}
    </div>
  );
}

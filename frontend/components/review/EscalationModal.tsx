/**
 * EscalationModal — hierarchical governance escalation with workflow routing.
 *
 * Features:
 * - Escalation reason (required)
 * - Workflow stage target picker (legal_approval, exec_approval, compliance)
 * - Priority bump selector (none, medium, high, critical)
 * - Escalation target (assignee) input
 * - Impact preview showing the full routing path
 * - Loading and error states
 */

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, X, AlertTriangle, User } from "lucide-react";

interface EscalationModalProps {
  reviewId: string;
  reviewTitle: string;
  currentPriority: string;
  currentStage: string | null;
  onEscalate: (reason: string, escalatedTo?: string, raisePriority?: boolean, targetStage?: string) => Promise<void>;
  onClose: () => void;
  isLoading?: boolean;
}

const WORKFLOW_STAGES = [
  {
    value: "legal_approval",
    label: "Legal Approval",
    description: "Route to legal team for review and final approval",
    targetStatus: "legal_approval",
    icon: "\u2696\uFE0F",
  },
  {
    value: "exec_approval",
    label: "Executive Approval",
    description: "Route to executive leadership for final decision",
    targetStatus: "exec_approval",
    icon: "\uD83C\uDFDB\uFE0F",
  },
  {
    value: "compliance",
    label: "Compliance Review",
    description: "Route to compliance team for regulatory assessment",
    targetStatus: "in_review",
    icon: "\uD83D\uDCCB",
  },
] as const;

const MIN_REASON_LENGTH = 5;

const PRIORITY_LEVELS = [
  { value: "", label: "None", description: "Keep current priority" },
  { value: "medium", label: "Medium", description: "Raise to medium priority" },
  { value: "high", label: "High", description: "Raise to high priority" },
  { value: "critical", label: "Critical", description: "Raise to critical priority" },
] as const;

function getPriorityColor(p: string): string {
  switch (p) {
    case "critical": return "bg-red-100 text-red-700";
    case "high": return "bg-orange-100 text-orange-700";
    case "medium": return "bg-amber-100 text-amber-700";
    default: return "bg-green-100 text-green-700";
  }
}

export function EscalationModal({
  reviewId,
  reviewTitle,
  currentPriority,
  currentStage,
  onEscalate,
  onClose,
  isLoading = false,
}: EscalationModalProps) {
  const [reason, setReason] = useState("");
  const [stage, setStage] = useState("");
  const [priorityLevel, setPriorityLevel] = useState("");
  const [assignee, setAssignee] = useState("");
  const [error, setError] = useState("");

  const selectedStage = WORKFLOW_STAGES.find((s) => s.value === stage);

  const handleEscalate = async () => {
    const trimmedReason = reason.trim();
    if (!trimmedReason) {
      setError("Escalation reason is required");
      return;
    }
    if (trimmedReason.length < MIN_REASON_LENGTH) {
      setError(`Please enter at least ${MIN_REASON_LENGTH} characters (${trimmedReason.length}/${MIN_REASON_LENGTH})`);
      return;
    }
    if (!stage) {
      setError("Target workflow stage is required");
      return;
    }

    try {
      const raisePriority = priorityLevel !== "";
      await onEscalate(trimmedReason, assignee || undefined, raisePriority, stage);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Escalation failed");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-orange-50 to-amber-50 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-navy-900">Escalate Review</h2>
            <p className="text-sm text-gray-500 mt-1">{reviewTitle}</p>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Current Context */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center gap-2 text-xs text-gray-600">
              <span className="font-medium">Priority:</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${getPriorityColor(currentPriority)}`}>{currentPriority}</span>
            </div>
            <span className="text-gray-300">|</span>
            <div className="flex items-center gap-2 text-xs text-gray-600">
              <span className="font-medium">Stage:</span>
              <span>{currentStage || "reviewer"}</span>
            </div>
          </div>

          {/* Escalation Reason */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Escalation Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => { setReason(e.target.value); setError(""); }}
              placeholder="Explain why this review needs escalation (e.g., unacceptable liability, requires legal interpretation, etc.)"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500"
              rows={3}
            />
            <p className={`mt-1 text-xs ${reason.trim().length >= MIN_REASON_LENGTH ? "text-gray-500" : "text-amber-600"}`}>
              {reason.trim().length}/{MIN_REASON_LENGTH} characters minimum
            </p>
          </div>

          {/* Target Workflow Stage */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Target Workflow Stage <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-1 gap-2">
              {WORKFLOW_STAGES.map((s) => (
                <label
                  key={s.value}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    stage === s.value
                      ? "bg-orange-50 border-orange-300 ring-1 ring-orange-300"
                      : "bg-white border-gray-200 hover:bg-gray-50"
                  }`}
                  onClick={() => { setStage(s.value); setError(""); }}
                >
                  <input
                    type="radio"
                    name="workflow-stage"
                    value={s.value}
                    checked={stage === s.value}
                    onChange={() => {}}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-base">{s.icon}</span>
                      <p className="text-sm font-medium text-gray-900">{s.label}</p>
                      <span className="text-[9px] font-mono bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        → {s.targetStatus}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Assignee (Escalation Target) */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Assign To <span className="text-gray-500">(Optional)</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                placeholder="user_id or email of the escalation target"
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>
          </div>

          {/* Priority Bump Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Priority Increase
            </label>
            <div className="grid grid-cols-4 gap-2">
              {PRIORITY_LEVELS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPriorityLevel(p.value)}
                  className={`px-2 py-2 text-xs font-medium rounded-lg border text-center transition-colors ${
                    priorityLevel === p.value
                      ? p.value === "critical"
                        ? "bg-red-50 border-red-300 text-red-700"
                        : p.value === "high"
                        ? "bg-orange-50 border-orange-300 text-orange-700"
                        : p.value === "medium"
                        ? "bg-amber-50 border-amber-300 text-amber-700"
                        : "bg-gray-50 border-gray-300 text-gray-700"
                      : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <p className="font-semibold">{p.label}</p>
                  <p className="text-[8px] mt-0.5 opacity-70">{p.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Escalation Impact Preview */}
          {selectedStage && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm font-medium text-blue-900 mb-2">Escalation Routing Path</p>
              <div className="flex items-center gap-2 text-xs text-blue-700 font-mono">
                <span className="px-2 py-1 bg-white rounded border border-blue-200">{currentStage || "in_review"}</span>
                <span className="text-blue-400">→</span>
                <span className="px-2 py-1 bg-orange-100 rounded border border-orange-200 text-orange-700 font-semibold">
                  {selectedStage.value}
                </span>
                <span className="text-blue-400">→</span>
                <span className="px-2 py-1 bg-white rounded border border-blue-200">{selectedStage.targetStatus}</span>
              </div>
              <div className="mt-2 flex items-center gap-2 text-xs text-blue-700">
                <span className="font-medium">Priority:</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${getPriorityColor(priorityLevel || currentPriority)}`}>
                  {priorityLevel || currentPriority}
                </span>
                {assignee && (
                  <>
                    <span className="text-blue-400">|</span>
                    <span className="font-medium">Assignee:</span>
                    <span>{assignee}</span>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 rounded-lg border border-red-200">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 px-6 py-4 border-t border-gray-100 bg-gray-50">
          {(reason.trim().length < MIN_REASON_LENGTH || !stage) && !isLoading && (
            <p className="mb-3 text-xs text-gray-600 text-center">
              {!stage && reason.trim().length >= MIN_REASON_LENGTH
                ? "Select a target workflow stage to continue."
                : reason.trim().length < MIN_REASON_LENGTH
                  ? `Enter at least ${MIN_REASON_LENGTH} characters for the reason (${reason.trim().length}/${MIN_REASON_LENGTH}).`
                  : `Complete the reason and select a workflow stage to continue.`}
            </p>
          )}
          <div className="flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleEscalate}
            disabled={isLoading || reason.trim().length < MIN_REASON_LENGTH || !stage}
            title={
              reason.trim().length < MIN_REASON_LENGTH
                ? `Add ${MIN_REASON_LENGTH - reason.trim().length} more character(s) in the reason field`
                : !stage
                  ? "Select a target workflow stage"
                  : undefined
            }
            className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-lg hover:bg-orange-700 disabled:cursor-not-allowed disabled:bg-gray-400 disabled:hover:bg-gray-400 transition-colors inline-flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Routing...
              </>
            ) : (
              <>
                <ArrowUpRight className="w-4 h-4" />
                Escalate & Route
              </>
            )}
          </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

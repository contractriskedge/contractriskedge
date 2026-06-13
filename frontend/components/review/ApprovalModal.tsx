/**
 * ApprovalModal — legal approval decision capture.
 *
 * Features:
 * - Approval comment textarea (required)
 * - Optional conditions JSON editor
 * - Risk acknowledgement checkbox
 * - Decision buttons (Approve / Reject / Cancel)
 * - Loading and error states
 */

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Check, X, AlertCircle } from "lucide-react";

interface ApprovalModalProps {
  reviewId: string;
  reviewTitle: string;
  riskScore?: number;
  openCriticalFindings?: number;
  openObligations?: number;
  onApprove: (decision: string, comment: string, conditions?: Record<string, unknown>) => Promise<void>;
  onReject: (comment: string, category?: string, severity?: string) => Promise<void>;
  onClose: () => void;
  isLoading?: boolean;
}

const REJECTION_CATEGORIES = [
  { value: "legal_risk", label: "Legal Risk", description: "Unacceptable legal exposure or liability terms" },
  { value: "compliance_issue", label: "Compliance Issue", description: "Violates regulatory or compliance requirements" },
  { value: "missing_clauses", label: "Missing Clauses", description: "Critical clauses absent from the agreement" },
  { value: "unacceptable_liability", label: "Unacceptable Liability", description: "Liability caps, indemnification, or risk allocation unacceptable" },
  { value: "data_privacy_issue", label: "Data Privacy Issue", description: "GDPR, CCPA, or data handling concerns" },
  { value: "other", label: "Other", description: "Reason not covered by categories above" },
] as const;

const SEVERITY_OPTIONS = [
  { value: "critical", label: "Critical", description: "Blocking issue — cannot proceed under any conditions" },
  { value: "high", label: "High", description: "Major issue — requires significant renegotiation" },
  { value: "medium", label: "Medium", description: "Moderate issue — should be addressed before approval" },
  { value: "low", label: "Low", description: "Minor issue — can be noted without blocking" },
] as const;

export function ApprovalModal({
  reviewId,
  reviewTitle,
  riskScore,
  openCriticalFindings = 0,
  openObligations = 0,
  onApprove,
  onReject,
  onClose,
  isLoading = false,
}: ApprovalModalProps) {
  const [decision, setDecision] = useState<"approve" | "reject" | null>(null);
  const [comment, setComment] = useState("");
  const [conditionsJson, setConditionsJson] = useState("");
  const [riskAck, setRiskAck] = useState(false);
  const [rejectionCategory, setRejectionCategory] = useState("");
  const [rejectionSeverity, setRejectionSeverity] = useState("");
  const [error, setError] = useState("");

  const handleApprove = async () => {
    if (!comment.trim()) {
      setError("Approval comment is required");
      return;
    }
    if (!riskAck) {
      setError("You must acknowledge the risk assessment");
      return;
    }

    // Critical findings guard: block unless override is provided
    if (openCriticalFindings > 0) {
      if (!comment.toLowerCase().includes("override:")) {
        setError(
          `${openCriticalFindings} critical/high finding(s) are still open. ` +
          "Add 'override:' at the start of your comments to acknowledge and bypass."
        );
        return;
      }
    }

    // Open obligations guard: block unless override is provided
    if (openObligations > 0) {
      if (!comment.toLowerCase().includes("override:")) {
        setError(
          `${openObligations} obligation(s) are still open. ` +
          "Complete or close all obligations before approving, or add 'override:' at the start of your comments."
        );
        return;
      }
    }

    try {
      let conditions: Record<string, unknown> | undefined;
      if (conditionsJson.trim()) {
        try {
          conditions = JSON.parse(conditionsJson);
        } catch {
          setError("Invalid JSON in conditions field");
          return;
        }
      }
      await onApprove("approved", comment, conditions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    }
  };

  const handleReject = async () => {
    if (!comment.trim()) {
      setError("Rejection reason is required");
      return;
    }
    if (!rejectionCategory) {
      setError("Rejection category is required");
      return;
    }
    if (!rejectionSeverity) {
      setError("Rejection severity is required");
      return;
    }

    try {
      const conditions = { category: rejectionCategory, severity: rejectionSeverity };
      await onReject(comment, rejectionCategory, rejectionSeverity);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rejection failed");
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
        className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-navy-900">Review Decision</h2>
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
          {/* Risk Score Display */}
          {riskScore !== undefined && (
            <div className={`p-4 rounded-lg border-l-4 ${
              riskScore >= 0.7
                ? "bg-red-50 border-red-400"
                : riskScore >= 0.5
                ? "bg-orange-50 border-orange-400"
                : "bg-amber-50 border-amber-400"
            }`}>
              <div className="flex items-center gap-2">
                <AlertCircle className={`w-5 h-5 ${
                  riskScore >= 0.7
                    ? "text-red-600"
                    : riskScore >= 0.5
                    ? "text-orange-600"
                    : "text-amber-600"
                }`} />
                <div>
                  <p className={`font-semibold text-sm ${
                    riskScore >= 0.7
                      ? "text-red-900"
                      : riskScore >= 0.5
                      ? "text-orange-900"
                      : "text-amber-900"
                  }`}>
                    Risk Assessment: {(riskScore * 100).toFixed(0)}%
                  </p>
                  <p className="text-xs text-gray-600 mt-0.5">
                    {riskScore >= 0.7
                      ? "High risk — requires careful review"
                      : riskScore >= 0.5
                      ? "Medium risk — verify key terms"
                      : "Low risk — standard review"}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Decision Tabs */}
          <div className="flex gap-2 border-b border-gray-200">
            <button
              onClick={() => { setDecision("approve"); setError(""); }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                decision === "approve"
                  ? "text-green-700 border-green-600"
                  : "text-gray-600 border-transparent hover:text-gray-900"
              }`}
            >
              <Check className="w-4 h-4 inline mr-2" />
              Approve
            </button>
            <button
              onClick={() => { setDecision("reject"); setError(""); }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                decision === "reject"
                  ? "text-red-700 border-red-600"
                  : "text-gray-600 border-transparent hover:text-gray-900"
              }`}
            >
              <X className="w-4 h-4 inline mr-2" />
              Reject
            </button>
          </div>

          {/* Decision-Specific Content */}
          {decision === "approve" && (
            <div className="space-y-4">
              {/* Critical Findings Warning */}
              {openCriticalFindings > 0 && (
                <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-red-900">
                        {openCriticalFindings} Critical/High Finding(s) Open
                      </p>
                      <p className="text-xs text-red-700 mt-0.5">
                        These findings must be resolved before approval, or you must include
                        {' '}<strong>"override:"</strong> at the start of your approval comment to bypass.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Open Obligations Warning */}
              {openObligations > 0 && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-amber-900">
                        {openObligations} Open Obligation(s)
                      </p>
                      <p className="text-xs text-amber-700 mt-0.5">
                        Complete or close all obligations before approving, or include
                        {' '}<strong>"override:"</strong> at the start of your approval comment to bypass.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Approval Comment */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Approval Comment <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => { setComment(e.target.value); setError(""); }}
                  placeholder="Enter approval comment (e.g., approved with no objections, all terms acceptable, etc.)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  rows={4}
                />
              </div>

              {/* Optional Conditions */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Conditions <span className="text-gray-500">(Optional)</span>
                </label>
                <textarea
                  value={conditionsJson}
                  onChange={(e) => setConditionsJson(e.target.value)}
                  placeholder={'{"required_by": "2026-06-30", "escalation_trigger": "policy_change"}'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  rows={3}
                />
                <p className="text-xs text-gray-500 mt-1">Valid JSON object for conditional approval terms</p>
              </div>

              {/* Risk Acknowledgement */}
              <label className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={riskAck}
                  onChange={(e) => { setRiskAck(e.target.checked); setError(""); }}
                  className="mt-1 w-4 h-4 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-blue-900">
                    I acknowledge the risk assessment and approve this contract
                  </p>
                  <p className="text-xs text-blue-700 mt-0.5">
                    By checking this box, you confirm that you have reviewed all findings and accept responsibility for this approval decision.
                  </p>
                </div>
              </label>
            </div>
          )}

          {decision === "reject" && (
            <div className="space-y-4">
              {/* Rejection Reason */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Rejection Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => { setComment(e.target.value); setError(""); }}
                  placeholder="Explain why this contract is being rejected (e.g., unacceptable liability limits, missing clauses, etc.)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                  rows={4}
                />
              </div>

              {/* Rejection Category */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Rejection Category <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-1 gap-2">
                  {REJECTION_CATEGORIES.map((cat) => (
                    <label
                      key={cat.value}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        rejectionCategory === cat.value
                          ? "bg-red-50 border-red-300"
                          : "bg-white border-gray-200 hover:bg-gray-50"
                      }`}
                      onClick={() => { setRejectionCategory(cat.value); setError(""); }}
                    >
                      <input
                        type="radio"
                        name="rejection-category"
                        value={cat.value}
                        checked={rejectionCategory === cat.value}
                        onChange={() => {}}
                        className="mt-0.5"
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{cat.label}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{cat.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Rejection Severity */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Severity <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {SEVERITY_OPTIONS.map((sev) => (
                    <label
                      key={sev.value}
                      className={`flex items-start gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                        rejectionSeverity === sev.value
                          ? "bg-red-50 border-red-300"
                          : "bg-white border-gray-200 hover:bg-gray-50"
                      }`}
                      onClick={() => { setRejectionSeverity(sev.value); setError(""); }}
                    >
                      <input
                        type="radio"
                        name="rejection-severity"
                        value={sev.value}
                        checked={rejectionSeverity === sev.value}
                        onChange={() => {}}
                        className="mt-0.5"
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{sev.label}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{sev.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Rejection Impact Note */}
              <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                <p className="text-sm text-red-900">
                  ⚠️ Rejection will send this contract back to the originating team for renegotiation or cancellation.
                </p>
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
        <div className="sticky bottom-0 px-6 py-4 border-t border-gray-100 bg-gray-50 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
          {decision === "approve" && (
            <button
              onClick={handleApprove}
              disabled={isLoading || !comment.trim() || !riskAck || (openCriticalFindings > 0 && !comment.toLowerCase().includes("override:")) || (openObligations > 0 && !comment.toLowerCase().includes("override:"))}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors inline-flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Approving...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Approve
                </>
              )}
            </button>
          )}
          {decision === "reject" && (
            <button
              onClick={handleReject}
              disabled={isLoading || !comment.trim() || !rejectionCategory || !rejectionSeverity}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors inline-flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Rejecting...
                </>
              ) : (
                <>
                  <X className="w-4 h-4" />
                  Reject
                </>
              )}
            </button>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

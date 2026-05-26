/**
 * RedlineEditModal — lawyer-in-the-loop editing for AI-suggested redlines.
 *
 * Shows:
 * - Original clause (read-only, red)
 * - AI suggestion (read-only, green)
 * - Editable textarea for reviewer's custom wording
 *
 * Actions:
 * - Accept AI Suggestion
 * - Modify & Accept (saves custom wording)
 * - Cancel
 */

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Check, X, Edit3 } from "lucide-react";
import type { RedlineItem } from "@/services/api/client";
import { RedlineContent } from "./RedlineContent";
import { FallbackClausePicker } from "./FallbackClausePicker";

interface RedlineEditModalProps {
  redline: RedlineItem;
  onAccept: (redlineId: string, reviewNotes?: string) => Promise<void>;
  onModify: (redlineId: string, modifiedText: string, reviewNotes?: string) => Promise<void>;
  onReject: (redlineId: string, reviewNotes?: string) => Promise<void>;
  onClose: () => void;
  isLoading?: boolean;
}

export function RedlineEditModal({
  redline,
  onAccept,
  onModify,
  onReject,
  onClose,
  isLoading = false,
}: RedlineEditModalProps) {
  const [customText, setCustomText] = useState(redline.proposed_text);
  const [reviewNotes, setReviewNotes] = useState("");
  const [mode, setMode] = useState<"view" | "edit">("view");

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
        className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-3xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-purple-50 to-indigo-50 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-navy-900">Edit Redline</h2>
            <p className="text-sm text-gray-500 mt-1">
              {redline.clause_type?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "Clause"}
              {redline.confidence != null && (
                <span className="ml-2 text-[10px] text-gray-400">
                  {(redline.confidence * 100).toFixed(0)}% AI confidence
                </span>
              )}
            </p>
          </div>
          <button onClick={onClose} disabled={isLoading} className="text-gray-400 hover:text-gray-600 disabled:opacity-50">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {mode === "view" ? (
            <div className="space-y-3">
              <RedlineContent redline={redline} />
              <button
                onClick={() => setMode("edit")}
                className="inline-flex items-center gap-1 text-xs font-medium text-purple-700 hover:text-purple-900"
              >
                <Edit3 className="w-3.5 h-3.5" /> Edit suggested wording
              </button>
            </div>
          ) : (
            <div className="rounded-lg border border-purple-200 bg-purple-50/50 overflow-hidden">
              <div className="px-4 py-2 bg-purple-100 border-b border-purple-200 flex items-center justify-between">
                <span className="text-xs font-semibold text-purple-700">Your Custom Version</span>
                <button
                  onClick={() => { setCustomText(redline.proposed_text); setMode("view"); }}
                  className="text-[10px] font-medium text-gray-500 hover:text-gray-700"
                >
                  Reset to AI
                </button>
              </div>
              <div className="px-4 py-3">
                <textarea
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-purple-300 rounded-lg focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 resize-y min-h-[120px]"
                  rows={6}
                />
              </div>
              {/* Playbook fallback clause picker — shown in edit mode */}
              <div className="px-4 pb-3">
                <FallbackClausePicker
                  clauseType={redline.clause_type}
                  currentText={customText}
                  onSelectFallback={(text) => setCustomText(text)}
                />
              </div>
            </div>
          )}

          {/* Rationale */}
          {redline.rationale && (
            <div className="px-4 py-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-[10px] font-semibold text-blue-700 mb-1">AI Rationale</p>
              <p className="text-xs text-blue-800">{redline.rationale}</p>
            </div>
          )}

          {/* Risk Level */}
          {redline.risk_level && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span className="font-medium">Risk Level:</span>
              <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold ${
                redline.risk_level === "critical" ? "bg-red-100 text-red-700" :
                redline.risk_level === "high" ? "bg-orange-100 text-orange-700" :
                redline.risk_level === "medium" ? "bg-amber-100 text-amber-700" :
                "bg-green-100 text-green-700"
              }`}>
                {redline.risk_level}
              </span>
            </div>
          )}

          {/* Review Notes */}
          <div className="rounded-lg border border-gray-200 bg-gray-50/50 overflow-hidden">
            <div className="px-4 py-2 bg-gray-100 border-b border-gray-200">
              <span className="text-xs font-semibold text-gray-600">Review Notes (optional)</span>
            </div>
            <div className="px-4 py-3">
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Add a note explaining your decision..."
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y min-h-[60px]"
                rows={3}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 px-6 py-4 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
          <button
            onClick={() => onReject(redline.redline_id, reviewNotes || undefined)}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 disabled:opacity-50 transition-colors inline-flex items-center gap-2"
          >
            <X className="w-4 h-4" /> Reject
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            {mode === "edit" && customText !== redline.proposed_text ? (
              <button
                onClick={() => onModify(redline.redline_id, customText, reviewNotes || undefined)}
                disabled={isLoading || !customText.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors inline-flex items-center gap-2"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Edit3 className="w-4 h-4" />
                )}
                Save Custom Version
              </button>
            ) : (
              <button
                onClick={() => onAccept(redline.redline_id, reviewNotes || undefined)}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors inline-flex items-center gap-2"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                Accept AI Suggestion
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

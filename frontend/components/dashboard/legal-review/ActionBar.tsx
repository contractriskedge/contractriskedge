"use client";

import React, { useState } from "react";
import {
  CheckCircle, XCircle, Download, ArrowUpCircle, MessageSquarePlus,
  Loader2, MoreHorizontal, FileDown
} from "lucide-react";
import type { SuggestionStatus } from "./types";

interface ActionBarProps {
  suggestionId: string;
  status: SuggestionStatus;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onEscalate: (id: string, reason: string) => void;
  onAddComment: (id: string) => void;
  onExportDocx: (id: string) => void;
  onExportPdf: (id: string) => void;
  actionLoading: string | null;
}

export function ActionBar({
  suggestionId,
  status,
  onAccept,
  onReject,
  onEscalate,
  onAddComment,
  onExportDocx,
  onExportPdf,
  actionLoading,
}: ActionBarProps) {
  const [showEscalate, setShowEscalate] = useState(false);
  const [escalateReason, setEscalateReason] = useState("");
  const [showMore, setShowMore] = useState(false);

  const isPending = status === "pending";
  const isLoading = actionLoading === suggestionId;

  const handleEscalate = () => {
    if (!escalateReason.trim()) return;
    onEscalate(suggestionId, escalateReason.trim());
    setEscalateReason("");
    setShowEscalate(false);
  };

  return (
    <div className="space-y-2">
      {/* Primary actions */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {isPending && (
          <>
            <button
              onClick={() => onAccept(suggestionId)}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
              Accept
            </button>
            <button
              onClick={() => onReject(suggestionId)}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white text-red-600 border border-red-200 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              Reject
            </button>
            <button
              onClick={() => setShowEscalate(!showEscalate)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white text-purple-600 border border-purple-200 hover:bg-purple-50 transition-colors"
            >
              <ArrowUpCircle className="w-3.5 h-3.5" />
              Escalate
            </button>
          </>
        )}

        <button
          onClick={() => onAddComment(suggestionId)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white text-navy-600 border border-navy-200 hover:bg-navy-50 transition-colors"
        >
          <MessageSquarePlus className="w-3.5 h-3.5" />
          Comment
        </button>

        {/* Export dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowMore(!showMore)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
            aria-label="Export options"
          >
            <Download className="w-3.5 h-3.5" />
            Export
            <MoreHorizontal className="w-3 h-3" />
          </button>
          {showMore && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMore(false)} />
              <div className="absolute right-0 top-full mt-1 z-20 w-36 bg-white rounded-lg border border-gray-200 shadow-lg py-1">
                <button
                  onClick={() => { onExportDocx(suggestionId); setShowMore(false); }}
                  className="w-full text-left px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                >
                  <FileDown className="w-3.5 h-3.5" />
                  Export as DOCX
                </button>
                <button
                  onClick={() => { onExportPdf(suggestionId); setShowMore(false); }}
                  className="w-full text-left px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                >
                  <FileDown className="w-3.5 h-3.5" />
                  Export as PDF
                </button>
              </div>
            </>
          )}
        </div>

        {/* Status badge for non-pending */}
        {!isPending && (
          <span className={`text-[11px] font-medium px-2 py-1 rounded-full ${
            status === "accepted" ? "bg-green-100 text-green-700" :
            status === "rejected" ? "bg-red-100 text-red-700" :
            "bg-purple-100 text-purple-700"
          }`}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
        )}
      </div>

      {/* Escalate reason input */}
      {showEscalate && (
        <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg space-y-2">
          <label htmlFor="escalate-reason" className="text-[11px] font-medium text-purple-800">
            Escalation Reason
          </label>
          <textarea
            id="escalate-reason"
            value={escalateReason}
            onChange={(e) => setEscalateReason(e.target.value)}
            placeholder="Why is this being escalated? (e.g., Low confidence, ambiguous clause, legal review required...)"
            rows={2}
            className="w-full text-xs border border-purple-200 rounded-md px-2.5 py-1.5 bg-white placeholder-gray-400 focus:border-purple-400 focus:ring-1 focus:ring-purple-400 resize-none"
          />
          <div className="flex justify-end gap-1.5">
            <button
              onClick={() => setShowEscalate(false)}
              className="text-xs px-2.5 py-1 rounded-md text-gray-600 hover:bg-gray-100 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleEscalate}
              disabled={!escalateReason.trim()}
              className="text-xs px-3 py-1 rounded-md bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Confirm Escalation
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

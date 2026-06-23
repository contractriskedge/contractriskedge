"use client";

import React from "react";
import {
  ChevronLeft, ChevronRight, CheckCircle, XCircle, ArrowUpCircle,
  SkipForward, List, RotateCcw, RefreshCw, ThumbsUp, ThumbsDown,
  Eye,
} from "lucide-react";

interface FindingNavigationProps {
  currentIndex: number;
  total: number;
  currentStatus?: string;
  onPrevious: () => void;
  onNext: () => void;
  onAccept?: () => void;
  onReject?: () => void;
  onIgnore?: () => void;
  onResolve: () => void;
  onReopen?: () => void;
  onEscalate: () => void;
  onSkip: () => void;
  onShowAll: () => void;
}

export function FindingNavigation({
  currentIndex, total, currentStatus, onPrevious, onNext,
  onAccept, onReject, onIgnore, onResolve, onReopen,
  onEscalate, onSkip, onShowAll,
}: FindingNavigationProps) {
  const isResolved = currentStatus === "resolved" || currentStatus === "accepted";
  const isPending = currentStatus === "open" || currentStatus === "in_review" || !currentStatus;

  return (
    <div className="flex items-center justify-between px-3 py-1.5 bg-navy-800 text-white rounded-lg text-[10px]">
      <div className="flex items-center gap-2">
        <span className="font-medium">
          Finding <span className="text-gold-400">{currentIndex + 1}</span> of {total}
        </span>
        <div className="h-3 w-px bg-navy-600" />
        <div className="flex items-center gap-0.5">
          <button
            onClick={onPrevious}
            disabled={currentIndex <= 0}
            className="p-0.5 rounded hover:bg-navy-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Previous finding"
          >
            <ChevronLeft className="w-3 h-3" />
          </button>
          <button
            onClick={onNext}
            disabled={currentIndex >= total - 1}
            className="p-0.5 rounded hover:bg-navy-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Next finding"
          >
            <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-1">
        {isResolved ? (
          <button
            onClick={onReopen}
            className="flex items-center gap-0.5 px-2 py-0.5 bg-amber-600 hover:bg-amber-700 rounded text-[9px] font-medium transition-colors"
          >
            <RotateCcw className="w-2.5 h-2.5" /> Reopen
          </button>
        ) : isPending ? (
          <>
            {onAccept && (
              <button onClick={onAccept}
                className="flex items-center gap-0.5 px-2 py-0.5 bg-emerald-600 hover:bg-emerald-700 rounded text-[9px] font-medium transition-colors"
              >
                <ThumbsUp className="w-2.5 h-2.5" /> Accept
              </button>
            )}
            {onReject && (
              <button onClick={onReject}
                className="flex items-center gap-0.5 px-2 py-0.5 bg-red-600 hover:bg-red-700 rounded text-[9px] font-medium transition-colors"
              >
                <ThumbsDown className="w-2.5 h-2.5" /> Reject
              </button>
            )}
            {onIgnore && (
              <button onClick={onIgnore}
                className="flex items-center gap-0.5 px-2 py-0.5 bg-gray-600 hover:bg-gray-500 rounded text-[9px] font-medium transition-colors"
              >
                <Eye className="w-2.5 h-2.5" /> Ignore
              </button>
            )}
            <button
              onClick={onResolve}
              className="flex items-center gap-0.5 px-2 py-0.5 bg-green-600 hover:bg-green-700 rounded text-[9px] font-medium transition-colors"
            >
              <CheckCircle className="w-2.5 h-2.5" /> Resolve
            </button>
            <button
              onClick={onSkip}
              className="flex items-center gap-0.5 px-2 py-0.5 bg-navy-600 hover:bg-navy-500 rounded text-[9px] font-medium transition-colors"
            >
              <SkipForward className="w-2.5 h-2.5" /> Skip
            </button>
            <button
              onClick={onEscalate}
              className="flex items-center gap-0.5 px-2 py-0.5 bg-red-600 hover:bg-red-700 rounded text-[9px] font-medium transition-colors"
            >
              <ArrowUpCircle className="w-2.5 h-2.5" /> Escalate
            </button>
          </>
        ) : (
          <>
            <button onClick={onReopen}
              className="flex items-center gap-0.5 px-2 py-0.5 bg-amber-600 hover:bg-amber-700 rounded text-[9px] font-medium transition-colors"
            >
              <RotateCcw className="w-2.5 h-2.5" /> Reopen
            </button>
            <button
              onClick={onSkip}
              className="flex items-center gap-0.5 px-2 py-0.5 bg-navy-600 hover:bg-navy-500 rounded text-[9px] font-medium transition-colors"
            >
              <SkipForward className="w-2.5 h-2.5" /> Skip
            </button>
          </>
        )}
        <div className="h-3 w-px bg-navy-600 mx-0.5" />
        <button
          onClick={onShowAll}
          className="flex items-center gap-0.5 px-2 py-0.5 hover:bg-navy-600 rounded text-[9px] transition-colors"
          title="Show all findings"
        >
          <List className="w-2.5 h-2.5" /> All
        </button>
      </div>
    </div>
  );
}

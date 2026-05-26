"use client";

import { motion } from "framer-motion";
import { UserCheck, AlertTriangle, FileText, Sparkles, ArrowRightLeft, ChartBar, ShieldAlert, CircleDashed } from "lucide-react";
import type { ReviewQueueItem } from "./types";

interface ReviewToolbarProps {
  selected?: ReviewQueueItem | null;
  selectedCount: number;
  onAssign: () => void;
  onEscalate: () => void;
  onApprove: () => void;
  onReject: () => void;
  onGenerateRedline: () => void;
  onCompareVersions: () => void;
}

export function ReviewToolbar({
  selected,
  selectedCount,
  onAssign,
  onEscalate,
  onApprove,
  onReject,
  onGenerateRedline,
  onCompareVersions,
}: ReviewToolbarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="sticky top-0 z-20 rounded-3xl border border-slate-200/70 bg-white/95 p-4 shadow-sm shadow-slate-200/20 backdrop-blur dark:border-navy-700 dark:bg-navy-900/95"
      aria-label="Review toolbar"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Review controls</p>
          <h2 className="mt-2 text-xl font-semibold text-navy-900 dark:text-white">
            {selected ? `${selected.contractName} · ${selected.vendor}` : "Select a review to begin"}
          </h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {selected
              ? `Status: ${selected.escalationStatus.replace(/_/g, " ")} · SLA remaining ${selected.slaRemaining}`
              : `${selectedCount} review items selected`}
          </p>
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <button
            onClick={onAssign}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-300 hover:bg-slate-100 transition dark:border-navy-700 dark:bg-navy-800 dark:text-slate-200 dark:hover:border-navy-600"
          >
            <UserCheck className="h-4 w-4" aria-hidden="true" />
            Assign reviewer
          </button>
          <button
            onClick={onEscalate}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-orange-200 bg-orange-50 px-4 py-2 text-sm font-semibold text-orange-700 hover:bg-orange-100 transition dark:border-orange-400/30 dark:bg-orange-500/10 dark:text-orange-200"
          >
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            Escalate issue
          </button>
          <button
            onClick={onGenerateRedline}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-navy-900 hover:border-slate-300 hover:bg-slate-50 transition dark:border-navy-700 dark:bg-navy-800 dark:text-white"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            AI redlines
          </button>
          <button
            onClick={onCompareVersions}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-navy-900 hover:border-slate-300 hover:bg-slate-50 transition dark:border-navy-700 dark:bg-navy-800 dark:text-white"
          >
            <ArrowRightLeft className="h-4 w-4" aria-hidden="true" />
            Compare versions
          </button>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-600 dark:text-slate-400">
        <span className="inline-flex items-center gap-2">
          <ShieldAlert className="h-3.5 w-3.5 text-orange-500" aria-hidden="true" />
          Workflow control ready
        </span>
        <span className="inline-flex items-center gap-2">
          <ChartBar className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
          Review analytics available
        </span>
      </div>
    </motion.div>
  );
}

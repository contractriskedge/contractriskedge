"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeftRight, Check, X, Sparkles, UserPlus, Download, Clock,
  Shield, AlertTriangle, GitBranch, FileText, Eye, Edit3,
  Columns, AlignLeft, FileDiff, MoreHorizontal, Play, Pause,
  ChevronDown, Search, SlidersHorizontal,
} from "lucide-react";
import type { CompareMode, PanelMode, NegotiationWorkflow, NegotiationStage } from "./types";

interface TopToolbarProps {
  contractTitle: string;
  counterparty: string;
  compareMode: CompareMode;
  panelMode: PanelMode;
  workflow: NegotiationWorkflow;
  onCompareModeChange: (mode: CompareMode) => void;
  onPanelModeChange: (mode: PanelMode) => void;
  onGenerateAiRedlines: () => void;
  onApproveAll: () => void;
  onRejectAll: () => void;
  onExport: () => void;
  onAssignReviewer: () => void;
  onStageChange: (stage: NegotiationStage) => void;
}

export function TopToolbar({
  contractTitle, counterparty, compareMode, panelMode, workflow,
  onCompareModeChange, onPanelModeChange, onGenerateAiRedlines,
  onApproveAll, onRejectAll, onExport, onAssignReviewer, onStageChange,
}: TopToolbarProps) {
  const [showWorkflowMenu, setShowWorkflowMenu] = useState(false);

  const stageColors: Record<NegotiationStage, string> = {
    drafting: "bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-gray-400",
    review: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    negotiating: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    approved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    executed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    escalated: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  const healthColor = workflow.healthScore >= 80 ? "text-green-600" :
    workflow.healthScore >= 60 ? "text-amber-600" : "text-red-600";

  return (
    <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
      {/* Main Toolbar Row */}
      <div className="flex items-center justify-between px-3 py-1.5">
        {/* Left: Contract Info */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-4 h-4 text-gold-500 flex-shrink-0" />
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-navy-900 dark:text-white truncate">{contractTitle}</h2>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">with {counterparty}</p>
            </div>
          </div>
          <div className="h-6 w-px bg-gray-200 dark:bg-navy-600" />
          {/* Stage Badge */}
          <div className="relative">
            {workflow.stage === "executed" || workflow.stage === "escalated" ? (
              <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium ${stageColors[workflow.stage]}`}>
                <span className="capitalize">{workflow.stage}</span>
              </span>
            ) : (
              <>
                <button
                  onClick={() => setShowWorkflowMenu(!showWorkflowMenu)}
                  className={`flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium ${stageColors[workflow.stage]}`}
                >
                  <span className="capitalize">{workflow.stage}</span>
                  <ChevronDown className="w-2.5 h-2.5" />
                </button>
                {showWorkflowMenu && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="absolute top-full left-0 mt-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-lg z-10 py-1 w-32"
                  >
                    {(["drafting", "review", "negotiating", "approved", "executed"] as NegotiationStage[]).map(stage => (
                      <button
                        key={stage}
                        onClick={() => { onStageChange(stage); setShowWorkflowMenu(false); }}
                        className={`w-full text-left px-3 py-1.5 text-[10px] hover:bg-gray-50 dark:hover:bg-navy-700 capitalize ${
                          workflow.stage === stage ? "text-gold-600 font-semibold" : "text-gray-600 dark:text-gray-300"
                        }`}
                      >
                        {stage}
                      </button>
                    ))}
                  </motion.div>
                )}
              </>
            )}
          </div>
          {/* SLA Timer */}
          <div className={`flex items-center gap-1 text-[10px] ${workflow.isOverdue ? "text-red-500" : "text-gray-500"}`}>
            <Clock className="w-3 h-3" />
            <span className="tabular-nums">
              {workflow.isOverdue ? "OVERDUE" : `${Math.floor(workflow.slaRemaining / 86400)}d remaining`}
            </span>
          </div>
          {/* Health Score */}
          <div className="flex items-center gap-1 text-[10px]">
            <Shield className={`w-3 h-3 ${healthColor}`} />
            <span className={`font-medium ${healthColor}`}>{workflow.healthScore}%</span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1">
          {/* Compare Mode Toggle */}
          <div className="flex items-center border border-gray-200 dark:border-navy-600 rounded-md overflow-hidden">
            <button
              onClick={() => onCompareModeChange("side-by-side")}
              className={`p-1.5 ${compareMode === "side-by-side" ? "bg-navy-100 dark:bg-navy-600 text-navy-700 dark:text-white" : "text-gray-400 hover:text-navy-600 dark:hover:text-gray-300"} transition-colors`}
              title="Side by side"
            >
              <Columns className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onCompareModeChange("inline")}
              className={`p-1.5 ${compareMode === "inline" ? "bg-navy-100 dark:bg-navy-600 text-navy-700 dark:text-white" : "text-gray-400 hover:text-navy-600 dark:hover:text-gray-300"} transition-colors`}
              title="Inline diff"
            >
              <AlignLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onCompareModeChange("unified")}
              className={`p-1.5 ${compareMode === "unified" ? "bg-navy-100 dark:bg-navy-600 text-navy-700 dark:text-white" : "text-gray-400 hover:text-navy-600 dark:hover:text-gray-300"} transition-colors`}
              title="Unified diff"
            >
              <FileDiff className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="w-px h-5 bg-gray-200 dark:bg-navy-600 mx-1" />

          {/* Panel Mode */}
          <button
            onClick={() => onPanelModeChange(panelMode === "edit" ? "review" : "edit")}
            className={`p-1.5 rounded-md transition-colors ${panelMode === "edit" ? "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400" : "text-gray-400 hover:text-navy-600 dark:hover:text-gray-300"}`}
            title={panelMode === "edit" ? "Review mode" : "Edit mode"}
          >
            {panelMode === "edit" ? <Edit3 className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>

          <div className="w-px h-5 bg-gray-200 dark:bg-navy-600 mx-1" />

          {/* AI Generate */}
          <button
            onClick={onGenerateAiRedlines}
            className="flex items-center gap-1 px-2 py-1.5 bg-purple-500 hover:bg-purple-600 text-white rounded-md text-[10px] font-medium transition-colors"
          >
            <Sparkles className="w-3 h-3" />
            AI Redlines
          </button>

          {/* Approve / Reject All */}
          <button
            onClick={onApproveAll}
            className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-md transition-colors"
            title="Approve all"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onRejectAll}
            className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
            title="Reject all"
          >
            <X className="w-3.5 h-3.5" />
          </button>

          <div className="w-px h-5 bg-gray-200 dark:bg-navy-600 mx-1" />

          {/* Assign */}
          <button
            onClick={onAssignReviewer}
            className="p-1.5 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 rounded-md transition-colors"
            title="Assign reviewer"
          >
            <UserPlus className="w-3.5 h-3.5" />
          </button>

          {/* Export */}
          <button
            onClick={onExport}
            className="p-1.5 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 rounded-md transition-colors"
            title="Export"
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          {/* More */}
          <button className="p-1.5 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 rounded-md transition-colors">
            <MoreHorizontal className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Secondary Bar: Approvers & Escalation */}
      <div className="flex items-center justify-between px-3 py-1 bg-gray-50 dark:bg-navy-900/50 border-t border-gray-100 dark:border-navy-700">
        <div className="flex items-center gap-3">
          <span className="text-[9px] text-gray-500 font-medium uppercase tracking-wider">Approval Chain</span>
          <div className="flex items-center gap-1.5">
            {workflow.approvers.map((approver, i) => (
              <React.Fragment key={approver.name}>
                {i > 0 && <ChevronDown className="w-2 h-2 text-gray-300 -rotate-90" />}
                <div className="flex items-center gap-1 px-1.5 py-0.5 bg-white dark:bg-navy-800 rounded border border-gray-200 dark:border-navy-600">
                  <div className="w-4 h-4 rounded-full bg-navy-400 flex items-center justify-center text-[7px] font-bold text-white">
                    {approver.avatar}
                  </div>
                  <span className="text-[9px] text-gray-600 dark:text-gray-300">{approver.name}</span>
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    approver.status === "approved" ? "bg-green-500" :
                    approver.status === "rejected" ? "bg-red-500" : "bg-amber-400"
                  }`} />
                </div>
              </React.Fragment>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {workflow.escalationLevel > 0 && (
            <span className="flex items-center gap-1 text-[9px] text-red-500 font-medium">
              <AlertTriangle className="w-2.5 h-2.5" />
              Escalation Level {workflow.escalationLevel}
            </span>
          )}
          <span className="text-[9px] text-gray-400">
            Updated {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
      </div>
    </div>
  );
}

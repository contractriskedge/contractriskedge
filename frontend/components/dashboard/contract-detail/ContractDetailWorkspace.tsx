"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Download, FileEdit, CheckCircle, XCircle, ArrowUpCircle, MessageSquare, Clock, User, MoreHorizontal } from "lucide-react";
import { ClauseNavigation } from "./ClauseNavigation";
import { DocumentViewer } from "./DocumentViewer";
import { RightPanel } from "./RightPanel";
import { ObligationsPanel, VersionHistory, ActivityTimeline } from "./ObligationsPanel";
import { mockContract, versionHistory, activityEvents, negotiationIssues, workflowState } from "./mockData";
import type { ClauseData } from "./types";
import { RISK_BG, RISK_TEXT, RISK_BG_LIGHT } from "./types";

type LeftTab = "clauses" | "obligations" | "versions" | "activity";

export function ContractDetailWorkspace() {
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>("cl-4");
  const [showRedlines, setShowRedlines] = useState(true);
  const [leftTab, setLeftTab] = useState<LeftTab>("clauses");
  const [contract] = useState(mockContract);

  const selectedClause = contract.clauses.find((c) => c.id === selectedClauseId) || null;

  const allObligations = contract.clauses.flatMap((c) => c.obligations);

  const handleAddComment = useCallback((clauseId: string, body: string) => {
    // In production, this would call the API
    console.log("Add comment to", clauseId, body);
  }, []);

  const handleBack = () => {
    // Navigate back to contracts list
    window.history.back();
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* ── Top Toolbar ── */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <button onClick={handleBack} className="p-1 rounded hover:bg-gray-100 text-gray-400 transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-sm font-semibold text-navy-900">{contract.name}</h1>
            <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
              <span>v{contract.version}</span>
              <span>•</span>
              <span>{contract.contractType}</span>
              <span>•</span>
              <span className={`inline-flex items-center gap-1 font-medium px-1.5 py-0.5 rounded-full ${RISK_BG_LIGHT[contract.riskLevel]} ${RISK_TEXT[contract.riskLevel]}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${RISK_BG[contract.riskLevel]}`} />
                Risk: {contract.riskScore}/10
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Workflow status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-navy-50 rounded-lg border border-navy-100 mr-2">
            <Clock className="w-3.5 h-3.5 text-navy-600" />
            <span className="text-[10px] font-medium text-navy-700">Legal Review</span>
            <span className="text-[9px] text-navy-500">{workflowState.slaRemaining}h remaining</span>
          </div>

          <button className="inline-flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors shadow-sm">
            <CheckCircle className="w-3.5 h-3.5" /> Approve
          </button>
          <button className="inline-flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-white border border-red-200 text-red-600 hover:bg-red-50 transition-colors">
            <XCircle className="w-3.5 h-3.5" /> Reject
          </button>
          <button className="inline-flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-white border border-purple-200 text-purple-600 hover:bg-purple-50 transition-colors">
            <ArrowUpCircle className="w-3.5 h-3.5" /> Escalate
          </button>
          <button className="inline-flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <FileEdit className="w-3.5 h-3.5" /> Redline
          </button>
          <button className="p-1.5 rounded hover:bg-gray-100 text-gray-400 transition-colors">
            <Download className="w-4 h-4" />
          </button>
          <button className="p-1.5 rounded hover:bg-gray-100 text-gray-400 transition-colors">
            <MoreHorizontal className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Main 3-Panel Layout ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Navigation */}
        <div className="w-56 flex-shrink-0 flex flex-col">
          {/* Left tabs */}
          <div className="flex border-b border-gray-200 bg-gray-50">
            {[
              { id: "clauses" as const, label: "Clauses", icon: "📋" },
              { id: "obligations" as const, label: "Obligations", icon: "✓" },
              { id: "versions" as const, label: "Versions", icon: "↻" },
              { id: "activity" as const, label: "Activity", icon: "⚡" },
            ].map((tab) => (
              <button key={tab.id} onClick={() => setLeftTab(tab.id)}
                className={`flex-1 text-[9px] font-medium py-2 text-center transition-colors ${
                  leftTab === tab.id ? "bg-white text-navy-900 border-b-2 border-navy-700" : "text-gray-500 hover:text-gray-700"
                }`}>
                {tab.label}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-hidden">
            {leftTab === "clauses" && (
              <ClauseNavigation clauses={contract.clauses} selectedClauseId={selectedClauseId} onSelectClause={setSelectedClauseId} />
            )}
            {leftTab === "obligations" && <ObligationsPanel obligations={allObligations} />}
            {leftTab === "versions" && <VersionHistory versions={versionHistory} />}
            {leftTab === "activity" && <ActivityTimeline events={activityEvents} />}
          </div>
        </div>

        {/* Center Panel: Document Viewer */}
        <div className="flex-1 flex flex-col min-w-0">
          <DocumentViewer
            clauses={contract.clauses}
            selectedClauseId={selectedClauseId}
            showRedlines={showRedlines}
            onShowRedlinesChange={setShowRedlines}
            onSelectClause={setSelectedClauseId}
          />
        </div>

        {/* Right Panel: AI Intelligence */}
        <div className="w-80 flex-shrink-0">
          <RightPanel
            clause={selectedClause}
            issues={negotiationIssues}
            workflow={workflowState}
            onAddComment={handleAddComment}
          />
        </div>
      </div>
    </div>
  );
}

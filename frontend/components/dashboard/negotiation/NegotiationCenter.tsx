"use client";

import React, { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare, PenTool, AlertTriangle, Clock, Brain, ArrowUpCircle,
  GitBranch, Target, PanelLeft, PanelRight, Activity,
} from "lucide-react";
import type {
  CompareMode, PanelMode, NegotiationStage, NegotiationKpi,
  FallbackClause, AiNegotiationInsight,
} from "./types";
import { mockNegotiationSession, mockNegotiationKpis } from "./mockData";
import { NegotiationKpiCards } from "./NegotiationKpiCards";
import { LeftSidebar } from "./LeftSidebar";
import { CenterPanel } from "./CenterPanel";
import { RightPanel } from "./RightPanel";
import { TopToolbar } from "./TopToolbar";
import { ActivityTimeline } from "./ActivityTimeline";
import { IssueDetailDrawer } from "./IssueDetailDrawer";
import { NegotiationClauseDrawer } from "./NegotiationClauseDrawer";

// ── Negotiation Center ───────────────────────────────────────────────────

export function NegotiationCenter() {
  const session = mockNegotiationSession;
  const kpis = mockNegotiationKpis;

  // State
  const [compareMode, setCompareMode] = useState<CompareMode>("inline");
  const [panelMode, setPanelMode] = useState<PanelMode>("review");
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
  const [showClauseDrawer, setShowClauseDrawer] = useState(false);
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [showActivityTimeline, setShowActivityTimeline] = useState(false);
  const [redlines, setRedlines] = useState(session.redlines);
  const [issues, setIssues] = useState(session.issues);

  // Redline count by clause
  const redlineCountByClause = useMemo(() => {
    const map: Record<string, number> = {};
    redlines.forEach(r => {
      map[r.clauseId] = (map[r.clauseId] || 0) + 1;
    });
    return map;
  }, [redlines]);

  // Current clause data
  const currentVersion = session.versions.find(v => v.id === session.currentVersionId);
  const clauses = currentVersion?.content || [];

  // Handlers
  const handleRedlineAccept = useCallback((redlineId: string) => {
    setRedlines(prev => prev.map(r => r.id === redlineId ? { ...r, status: "accepted" as const } : r));
  }, []);

  const handleRedlineReject = useCallback((redlineId: string) => {
    setRedlines(prev => prev.map(r => r.id === redlineId ? { ...r, status: "rejected" as const } : r));
  }, []);

  const handleIssueStatusChange = useCallback((issueId: string, status: string) => {
    setIssues(prev => prev.map(i => i.id === issueId ? { ...i, status: status as any } : i));
  }, []);

  const handleIssueEscalate = useCallback((issueId: string) => {
    setIssues(prev => prev.map(i => i.id === issueId ? { ...i, escalationLevel: Math.min(i.escalationLevel + 1, 3), status: "escalated" as const } : i));
  }, []);

  const handleApplyInsight = useCallback((insight: AiNegotiationInsight) => {
    // In a real app, this would apply the AI suggestion to the document
    console.log("Applied insight:", insight.id);
  }, []);

  const handleApplyFallback = useCallback((fb: FallbackClause) => {
    // In a real app, this would insert the fallback clause
    console.log("Applied fallback:", fb.id);
  }, []);

  const handleClauseSelect = useCallback((clauseId: string) => {
    setActiveClauseId(clauseId);
    setShowClauseDrawer(true);
  }, []);

  const handleGenerateAiRedlines = useCallback(() => {
    // In a real app, this would trigger AI redline generation
    console.log("Generating AI redlines...");
  }, []);

  const handleStageChange = useCallback((stage: NegotiationStage) => {
    // In a real app, this would update the workflow stage
    console.log("Stage changed to:", stage);
  }, []);

  const activeIssue = issues.find(i => i.id === activeIssueId) || null;
  const activeClause = clauses.find(c => c.clauseId === activeClauseId) || null;

  // Get original and modified text for the active clause
  const originalVersion = session.versions.find(v => v.id === "v1");
  const originalClause = originalVersion?.content.find(c => c.clauseId === activeClauseId);
  const modifiedClause = clauses.find(c => c.clauseId === activeClauseId);
  const activeClauseOriginalText = originalClause?.content || modifiedClause?.content || "";
  const activeClauseModifiedText = modifiedClause?.content || "";
  const activeClauseComments = redlines
    .filter(r => r.clauseId === activeClauseId)
    .flatMap(r => r.comments)
    .concat(issues.filter(i => i.clauseId === activeClauseId).flatMap(i => i.comments));

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
      {/* KPI Row */}
      <div className="px-4 pt-3 pb-2">
        <NegotiationKpiCards metrics={kpis} />
      </div>

      {/* Top Toolbar */}
      <TopToolbar
        contractTitle={session.contractTitle}
        counterparty={session.counterparty}
        compareMode={compareMode}
        panelMode={panelMode}
        workflow={session.workflow}
        onCompareModeChange={setCompareMode}
        onPanelModeChange={setPanelMode}
        onGenerateAiRedlines={handleGenerateAiRedlines}
        onApproveAll={() => redlines.filter(r => r.status === "pending").forEach(r => handleRedlineAccept(r.id))}
        onRejectAll={() => redlines.filter(r => r.status === "pending").forEach(r => handleRedlineReject(r.id))}
        onExport={() => {}}
        onAssignReviewer={() => {}}
        onStageChange={handleStageChange}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex min-h-0">
        {/* Left Sidebar Toggle */}
        {!showLeftSidebar && (
          <button
            onClick={() => setShowLeftSidebar(true)}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 transition-colors"
            title="Show sidebar"
          >
            <PanelLeft className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Left Sidebar */}
        <AnimatePresence>
          {showLeftSidebar && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 288, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden flex-shrink-0"
            >
              <LeftSidebar
                issues={issues}
                clauses={clauses}
                participants={session.participants}
                playbooks={session.playbooks}
                activeClauseId={activeClauseId}
                activeIssueId={activeIssueId}
                redlineCountByClause={redlineCountByClause}
                onClauseSelect={handleClauseSelect}
                onIssueSelect={setActiveIssueId}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Center Panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Toggle buttons */}
          <div className="flex items-center justify-between px-2 py-0.5 bg-gray-50 dark:bg-navy-900 border-b border-gray-200 dark:border-navy-700">
            <button
              onClick={() => setShowLeftSidebar(!showLeftSidebar)}
              className="flex items-center gap-1 text-[9px] text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 transition-colors"
            >
              <PanelLeft className="w-3 h-3" />
              {showLeftSidebar ? "Hide" : "Show"} sidebar
            </button>
            <button
              onClick={() => setShowActivityTimeline(!showActivityTimeline)}
              className={`flex items-center gap-1 text-[9px] transition-colors ${
                showActivityTimeline ? "text-gold-600" : "text-gray-400 hover:text-navy-600 dark:hover:text-gray-300"
              }`}
            >
              <Activity className="w-3 h-3" />
              Timeline
            </button>
            <button
              onClick={() => setShowRightPanel(!showRightPanel)}
              className="flex items-center gap-1 text-[9px] text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 transition-colors"
            >
              {showRightPanel ? "Hide" : "Show"} AI
              <PanelRight className="w-3 h-3" />
            </button>
          </div>

          {/* Activity Timeline (collapsible) */}
          <AnimatePresence>
            {showActivityTimeline && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="px-3 py-2 border-b border-gray-200 dark:border-navy-700">
                  <ActivityTimeline activities={session.activities} maxItems={5} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Center Panel */}
          <div className="flex-1 min-h-0">
            <CenterPanel
              clauses={clauses}
              redlines={redlines}
              activeClauseId={activeClauseId}
              compareMode={compareMode}
              panelMode={panelMode}
              versions={session.versions}
              currentVersionId={session.currentVersionId}
              insights={session.insights}
              onRedlineAccept={handleRedlineAccept}
              onRedlineReject={handleRedlineReject}
            />
          </div>
        </div>

        {/* Right Panel */}
        <AnimatePresence>
          {showRightPanel && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden flex-shrink-0"
            >
              <RightPanel
                insights={session.insights}
                playbooks={session.playbooks}
                analytics={session.analytics}
                onApplyInsight={handleApplyInsight}
                onApplyFallback={handleApplyFallback}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Issue Detail Drawer */}
      <IssueDetailDrawer
        issue={activeIssue}
        isOpen={!!activeIssueId}
        onClose={() => setActiveIssueId(null)}
        onStatusChange={handleIssueStatusChange}
        onEscalate={handleIssueEscalate}
      />

      {/* Clause Detail Drawer */}
      <NegotiationClauseDrawer
        clause={activeClause}
        originalText={activeClauseOriginalText}
        modifiedText={activeClauseModifiedText}
        redlines={redlines}
        insights={session.insights}
        playbooks={session.playbooks}
        comments={activeClauseComments}
        isOpen={showClauseDrawer && !!activeClause}
        onClose={() => setShowClauseDrawer(false)}
        onApplyFallback={handleApplyFallback}
      />
    </div>
  );
}

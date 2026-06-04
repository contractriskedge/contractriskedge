"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare, PenTool, AlertTriangle, Clock, Brain, ArrowUpCircle,
  GitBranch, Target, PanelLeft, PanelRight, Activity,
} from "lucide-react";
import type {
  CompareMode, PanelMode, NegotiationStage, NegotiationKpi,
  FallbackClause, AiNegotiationInsight,
} from "./types";
import { negotiationsService } from "@/services/api/negotiations";
import { NegotiationKpiCards } from "./NegotiationKpiCards";
import { LeftSidebar } from "./LeftSidebar";
import { CenterPanel } from "./CenterPanel";
import { RightPanel } from "./RightPanel";
import { TopToolbar } from "./TopToolbar";
import { ActivityTimeline } from "./ActivityTimeline";
import { IssueDetailDrawer } from "./IssueDetailDrawer";
import { NegotiationClauseDrawer } from "./NegotiationClauseDrawer";

// ── Hooks ───────────────────────────────────────────────────────

function useNegotiationSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["negotiation", sessionId],
    queryFn: () => negotiationsService.getSession(sessionId!),
    enabled: !!sessionId,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

function useNegotiationKpis() {
  return useQuery({
    queryKey: ["negotiation-kpis"],
    queryFn: () => negotiationsService.getKpis(),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

function useSessions() {
  return useQuery({
    queryKey: ["negotiations-list"],
    queryFn: () => negotiationsService.listSessions({ page_size: 50 }),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

function useActivities(sessionId: string | null) {
  return useQuery({
    queryKey: ["negotiation-activities", sessionId],
    queryFn: () => negotiationsService.getActivities(sessionId!),
    enabled: !!sessionId,
    staleTime: 15_000,
    gcTime: 30_000,
  });
}

// ── Negotiation Center ───────────────────────────────────────────────────

export function NegotiationCenter() {
  const queryClient = useQueryClient();

  // State
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState<CompareMode>("inline");
  const [panelMode, setPanelMode] = useState<PanelMode>("review");
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
  const [showClauseDrawer, setShowClauseDrawer] = useState(false);
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [showActivityTimeline, setShowActivityTimeline] = useState(false);

  // Queries
  const { data: sessionsData } = useSessions();
  const { data: session, isLoading: sessionLoading } = useNegotiationSession(selectedSessionId);
  const { data: kpisData } = useNegotiationKpis();
  const { data: activities } = useActivities(selectedSessionId);

  // Auto-select first session
  const sessions = sessionsData?.data ?? [];
  React.useEffect(() => {
    if (!selectedSessionId && sessions.length > 0) {
      setSelectedSessionId(sessions[0].id);
    }
  }, [sessions, selectedSessionId]);

  // Derive local state from session data
  const [localRedlines, setLocalRedlines] = useState<any[]>([]);
  const [localIssues, setLocalIssues] = useState<any[]>([]);

  React.useEffect(() => {
    if (session) {
      setLocalRedlines(session.redlines);
      setLocalIssues(session.issues);
    }
  }, [session]);

  // Build KPI cards from API data
  const kpiCards: NegotiationKpi[] = React.useMemo(() => {
    const k = kpisData;
    if (!k) return [];
    return [
      {
        id: "total",
        label: "Total Sessions",
        value: String(k.total_sessions),
        trend: 0, trendDirection: "neutral",
        icon: "GitBranch", color: "blue", severity: "info",
        sparklineData: [], tooltip: "Total negotiation sessions",
      },
      {
        id: "active",
        label: "Active",
        value: String(k.active_sessions),
        trend: 0, trendDirection: "neutral",
        icon: "Activity", color: "green", severity: "success",
        sparklineData: [], tooltip: "Active negotiations in progress",
      },
      {
        id: "escalated",
        label: "Escalated",
        value: String(k.escalated_count),
        trend: 0, trendDirection: "neutral",
        icon: "AlertTriangle", color: "red", severity: "critical",
        sparklineData: [], tooltip: "Escalated negotiations requiring attention",
      },
      ...Object.entries(k.by_stage).map(([stage, count]) => ({
        id: `stage-${stage}`,
        label: stage.charAt(0).toUpperCase() + stage.slice(1),
        value: String(count),
        trend: 0, trendDirection: "neutral" as const,
        icon: "Target", color: "amber", severity: "info" as const,
        sparklineData: [] as number[], tooltip: `Sessions in ${stage} stage`,
      })),
    ];
  }, [kpisData]);

  // Redline count by clause
  const redlineCountByClause = useMemo(() => {
    const map: Record<string, number> = {};
    localRedlines.forEach((r: any) => {
      map[r.clauseId] = (map[r.clauseId] || 0) + 1;
    });
    return map;
  }, [localRedlines]);

  // Current clause data
  const currentVersion = session?.versions.find((v: any) => v.id === session.currentVersionId);
  const clauses = currentVersion?.content || [];

  // Handlers
  const handleRedlineAccept = useCallback((redlineId: string) => {
    if (!selectedSessionId) return;
    negotiationsService.updateRedlineStatus(selectedSessionId, redlineId, { status: "accepted" })
      .then(() => {
        setLocalRedlines(prev => prev.map((r: any) => r.id === redlineId ? { ...r, status: "accepted" } : r));
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      });
  }, [selectedSessionId, queryClient]);

  const handleRedlineReject = useCallback((redlineId: string) => {
    if (!selectedSessionId) return;
    negotiationsService.updateRedlineStatus(selectedSessionId, redlineId, { status: "rejected" })
      .then(() => {
        setLocalRedlines(prev => prev.map((r: any) => r.id === redlineId ? { ...r, status: "rejected" } : r));
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      });
  }, [selectedSessionId, queryClient]);

  const handleIssueStatusChange = useCallback((issueId: string, status: string) => {
    if (!selectedSessionId) return;
    negotiationsService.updateIssue(selectedSessionId, issueId, { status })
      .then(() => {
        setLocalIssues(prev => prev.map((i: any) => i.id === issueId ? { ...i, status } : i));
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      });
  }, [selectedSessionId, queryClient]);

  const handleIssueEscalate = useCallback((issueId: string) => {
    if (!selectedSessionId) return;
    const issue = localIssues.find((i: any) => i.id === issueId);
    if (!issue) return;
    const newLevel = Math.min((issue.escalationLevel || 0) + 1, 3);
    negotiationsService.updateIssue(selectedSessionId, issueId, { escalationLevel: newLevel, status: "escalated" })
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      });
  }, [selectedSessionId, localIssues, queryClient]);

  const handleApplyInsight = useCallback((insight: AiNegotiationInsight) => {
    console.log("Applied insight:", insight.id);
  }, []);

  const handleApplyFallback = useCallback((fb: FallbackClause) => {
    console.log("Applied fallback:", fb.id);
  }, []);

  const handleClauseSelect = useCallback((clauseId: string) => {
    setActiveClauseId(clauseId);
    setShowClauseDrawer(true);
  }, []);

  const handleGenerateAiRedlines = useCallback(() => {
    console.log("Generating AI redlines...");
  }, []);

  const handleStageChange = useCallback((stage: NegotiationStage) => {
    if (!selectedSessionId) return;
    negotiationsService.updateSession(selectedSessionId, { stage })
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
        queryClient.invalidateQueries({ queryKey: ["negotiation-kpis"] });
      });
  }, [selectedSessionId, queryClient]);

  // Loading state
  if (sessionLoading && !session) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-navy-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-600 mx-auto mb-4" />
          <p className="text-gray-500 text-sm">Loading negotiation session...</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!session && sessions.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-navy-900">
        <div className="text-center max-w-md">
          <GitBranch className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-navy-800 dark:text-white mb-2">No Negotiations</h3>
          <p className="text-gray-500 text-sm mb-4">
            Create a negotiation session from a contract review to start tracking redlines, issues, and counter-party discussions.
          </p>
        </div>
      </div>
    );
  }

  if (!session) return null;

  const activeIssue = localIssues.find((i: any) => i.id === activeIssueId) || null;
  const activeClause = clauses.find((c: any) => c.clauseId === activeClauseId) || null;

  // Get original and modified text for the active clause
  const originalVersion = session.versions.find((v: any) => v.status === "superseded");
  const originalClause = originalVersion?.content.find((c: any) => c.clauseId === activeClauseId);
  const modifiedClause = clauses.find((c: any) => c.clauseId === activeClauseId);
  const activeClauseOriginalText = originalClause?.content || modifiedClause?.content || "";
  const activeClauseModifiedText = modifiedClause?.content || "";
  const activeClauseComments = localRedlines
    .filter((r: any) => r.clauseId === activeClauseId)
    .flatMap((r: any) => r.comments)
    .concat(localIssues.filter((i: any) => i.clauseId === activeClauseId).flatMap((i: any) => i.comments));

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
      {/* KPI Row */}
      <div className="px-4 pt-3 pb-2">
        <NegotiationKpiCards metrics={kpiCards} />
      </div>

      {/* Top Toolbar */}
      <TopToolbar
        contractTitle={session.contractTitle}
        counterparty={session.counterparty}
        compareMode={compareMode}
        panelMode={panelMode}
        workflow={{
          id: session.id,
          stage: session.stage as NegotiationStage,
          slaDeadline: "",
          slaRemaining: 0,
          approvers: [],
          escalationLevel: 0,
          isOverdue: false,
          healthScore: session.healthScore,
        }}
        onCompareModeChange={setCompareMode}
        onPanelModeChange={setPanelMode}
        onGenerateAiRedlines={handleGenerateAiRedlines}
        onApproveAll={() => localRedlines.filter((r: any) => r.status === "pending").forEach((r: any) => handleRedlineAccept(r.id))}
        onRejectAll={() => localRedlines.filter((r: any) => r.status === "pending").forEach((r: any) => handleRedlineReject(r.id))}
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
                issues={localIssues}
                clauses={clauses}
                participants={session.participants}
                playbooks={[]}
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
                  <ActivityTimeline activities={(activities || []) as any} maxItems={5} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Center Panel */}
          <div className="flex-1 min-h-0">
            <CenterPanel
              clauses={clauses}
              redlines={localRedlines}
              activeClauseId={activeClauseId}
              compareMode={compareMode}
              panelMode={panelMode}
              versions={session.versions}
              currentVersionId={session.currentVersionId}
              insights={[]}
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
                insights={[]}
                playbooks={[]}
                analytics={{}}
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
        redlines={localRedlines}
        insights={[]}
        playbooks={[]}
        comments={activeClauseComments}
        isOpen={showClauseDrawer && !!activeClause}
        onClose={() => setShowClauseDrawer(false)}
        onApplyFallback={handleApplyFallback}
      />
    </div>
  );
}


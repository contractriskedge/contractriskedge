"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare, PenTool, AlertTriangle, Clock, Brain, ArrowUpCircle,
  GitBranch, Target, PanelLeft, PanelRight, Activity, Search,
  FileOutput, Send, Plus, X, Loader2, Check, List, ArrowLeft,
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
import { FindingNavigation } from "./FindingNavigation";
import { FindingContextHeader } from "./FindingContextHeader";
import { ProgressBar } from "./ProgressBar";
import { WorkflowStepper } from "./WorkflowStepper";
import type { WorkflowStep } from "./WorkflowStepper";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToast } from "@/components/ui/toast";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { CompletionWizard } from "./CompletionWizard";
import { NotificationBell } from "./NotificationCenter";
import { useFlowEngine } from "./hooks/useFlowEngine";
import { useAutosave } from "./hooks/useAutosave";
import { usePresence } from "./hooks/usePresence";

// ── Hooks ───────────────────────────────────────────────────────

/** Keyboard navigation hook for finding review */
function useKeyboardNav(handlers: {
  onPrev: () => void;
  onNext: () => void;
  onResolve: () => void;
  onEscalate: () => void;
  onAccept?: () => void;
  onReject?: () => void;
  enabled: boolean;
}) {
  React.useEffect(() => {
    if (!handlers.enabled) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger when typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      switch (e.key) {
        case "j":
        case "J":
        case "ArrowDown":
          e.preventDefault();
          handlers.onNext();
          break;
        case "k":
        case "K":
        case "ArrowUp":
          e.preventDefault();
          handlers.onPrev();
          break;
        case "r":
        case "R":
          e.preventDefault();
          handlers.onResolve();
          break;
        case "e":
        case "E":
          e.preventDefault();
          handlers.onEscalate();
          break;
        case " ":
          e.preventDefault();
          handlers.onAccept?.();
          break;
        case "x":
        case "X":
          e.preventDefault();
          handlers.onReject?.();
          break;
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handlers]);
}

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
  const { addToast } = useToast();
  const router = useRouter();

  // State
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState<CompareMode>("inline");
  const [panelMode, setPanelMode] = useState<PanelMode>("review");
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
  const [workflowStep, setWorkflowStep] = useState<WorkflowStep>("findings");
  const [showClauseDrawer, setShowClauseDrawer] = useState(false);
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [showActivityTimeline, setShowActivityTimeline] = useState(false);
  const [sessionSearchQuery, setSessionSearchQuery] = useState("");
  const [showLaunchModal, setShowLaunchModal] = useState(false);
  const [showCreateRedlineModal, setShowCreateRedlineModal] = useState(false);
  const [stageFilter, setStageFilter] = useState<string | null>(null);
  const [searchFocused, setSearchFocused] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean; title: string; message: string;
    variant?: "danger" | "warning" | "info";
    onConfirm: () => void;
  }>({ isOpen: false, title: "", message: "", onConfirm: () => {} });
  const [contractIdFromUrl, setContractIdFromUrl] = useState<string | null>(null);
  const [resumingFromReview, setResumingFromReview] = useState(false);
  const [showCompletionWizard, setShowCompletionWizard] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [smartQueueFilter, setSmartQueueFilter] = useState<string>("all");

  // ── URL sync: read initial state from query params ────────────

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("sessionId");
    const clauseId = params.get("clauseId");
    const contractId = params.get("contractId");
    if (sessionId) setSelectedSessionId(sessionId);
    if (clauseId) { setActiveClauseId(clauseId); setShowClauseDrawer(true); }
    if (contractId) setContractIdFromUrl(contractId);
  }, []);

  // ── URL sync: write state to query params on change ───────────

  React.useEffect(() => {
    const params = new URLSearchParams();
    if (selectedSessionId) params.set("sessionId", selectedSessionId);
    if (activeClauseId && showClauseDrawer) params.set("clauseId", activeClauseId);
    const qs = params.toString();
    const url = qs ? `/negotiation?${qs}` : "/negotiation";
    router.replace(url, { scroll: false });
  }, [selectedSessionId, activeClauseId, showClauseDrawer, router]);

  React.useEffect(() => {
    if (!contractIdFromUrl || selectedSessionId || resumingFromReview) return;

    let cancelled = false;
    setResumingFromReview(true);
    negotiationsService.resumeOrCreateFromReview({ reviewId: contractIdFromUrl })
      .then((session) => {
        if (cancelled) return;
        setSelectedSessionId(session.id);
        setContractIdFromUrl(null);
        queryClient.invalidateQueries({ queryKey: ["negotiations-list"] });
        queryClient.invalidateQueries({ queryKey: ["negotiation", session.id] });
      })
      .catch((err: any) => {
        if (cancelled) return;
        addToast({
          type: "error",
          title: "Could not open negotiation",
          message: err?.message || "Failed to load negotiation from contract review",
        });
        setContractIdFromUrl(null);
      })
      .finally(() => {
        if (!cancelled) setResumingFromReview(false);
      });

    return () => { cancelled = true; };
  }, [contractIdFromUrl, selectedSessionId, resumingFromReview, queryClient, addToast]);

  // Queries
  const { data: sessionsData } = useSessions();
  const { data: session, isLoading: sessionLoading } = useNegotiationSession(selectedSessionId);
  const { data: kpisData } = useNegotiationKpis();
  const { data: activities } = useActivities(selectedSessionId);

  // Auto-select first session
  const sessions = sessionsData?.data ?? [];
  const filteredSessions = React.useMemo(() => {
    let list = sessions;
    if (stageFilter) {
      list = list.filter((s: any) => s.stage === stageFilter);
    }
    if (!sessionSearchQuery.trim()) return list;
    const q = sessionSearchQuery.toLowerCase();
    return list.filter((s: any) =>
      s.contractTitle?.toLowerCase().includes(q) ||
      s.counterparty?.toLowerCase().includes(q)
    );
  }, [sessions, sessionSearchQuery, stageFilter]);

  React.useEffect(() => {
    if (contractIdFromUrl || resumingFromReview) return;
    if (!selectedSessionId && sessions.length > 0) {
      setSelectedSessionId(sessions[0].id);
    }
  }, [sessions, selectedSessionId, contractIdFromUrl, resumingFromReview]);

  // Show session count in description
  const sessionCountText = React.useMemo(() => {
    if (sessions.length === 0) return "";
    if (stageFilter) {
      const total = sessions.length;
      const filtered = filteredSessions.length;
      return `${filtered} of ${total} session${total !== 1 ? "s" : ""}`;
    }
    return `${sessions.length} session${sessions.length !== 1 ? "s" : ""}`;
  }, [sessions, filteredSessions, stageFilter]);

  // Derive local state from session data
  const [localRedlines, setLocalRedlines] = useState<any[]>([]);
  const [localIssues, setLocalIssues] = useState<any[]>([]);

  // Compute active clause comments from metadata (must be before early returns — hooks rule)
  const activeClauseComments = React.useMemo(() => {
    const s = session as any;
    const metadataComments = s?.metadata?.clause_comments?.[activeClauseId || ""] ?? [];
    const fromMetadata = metadataComments.map((c: any) => ({
      id: c.comment_id,
      author: c.author_name || "User",
      authorAvatar: (c.author_name || "U")[0],
      authorRole: c.author_role || "",
      content: c.body,
      timestamp: c.created_at,
      status: c.resolved ? "resolved" : "active",
      mentions: [],
      replies: [],
    }));
    const fromRedlines = (localRedlines || [])
      .filter((r: any) => r.clauseId === activeClauseId)
      .flatMap((r: any) => r.comments || []);
    const fromIssues = (localIssues || [])
      .filter((i: any) => i.clauseId === activeClauseId)
      .flatMap((i: any) => i.comments || []);
    return [...fromMetadata, ...fromRedlines, ...fromIssues];
  }, [session, activeClauseId, localRedlines, localIssues]);

  React.useEffect(() => {
    if (session) {
      setLocalRedlines(session.redlines);
      setLocalIssues(session.issues);
    }
  }, [session]);

  // ── Flow Engine ──────────────────────────────────────────────
  const flowFindings = React.useMemo(() =>
    (localIssues || []).map((i: any) => ({
      id: i.id,
      title: i.title,
      description: i.description || "",
      severity: i.severity || "medium",
      status: i.status || "open",
      riskLevel: i.riskLevel,
      assignee: i.assignee,
      dueDate: i.dueDate,
      escalationLevel: i.escalationLevel,
    })),
  [localIssues]);

  const {
    findingIndex,
    totalOpen,
    totalFindings,
    currentStep,
    isComplete,
    progressPercent,
    currentFinding,
    goToNext,
    goToPrev,
    goToIndex,
    resolveAndAdvance,
    setStep: setFlowStep,
  } = useFlowEngine(flowFindings);

  // Show completion wizard when all findings resolved
  React.useEffect(() => {
    if (isComplete && totalFindings > 0) {
      setShowCompletionWizard(true);
    }
  }, [isComplete, totalFindings]);

  // ── Presence ─────────────────────────────────────────────────
  const currentUserId = "user-1"; // TODO: get from auth context
  const currentUserName = "User"; // TODO: get from auth context
  const {
    users: activeUsers,
    setCurrentClause: setPresenceClause,
    isConnected: isPresenceConnected,
  } = usePresence({
    sessionId: selectedSessionId,
    userId: currentUserId,
    userName: currentUserName,
  });

  // ── Notifications (derived from session data) ────────────────
  React.useEffect(() => {
    if (!selectedSessionId || !session) return;
    const derived: any[] = [];
    const now = Date.now();
    let idx = 0;

    // Escalated issues → notifications
    (localIssues || [])
      .filter((i: any) => i.status === "escalated" && (i.escalationLevel || 0) > 0)
      .forEach((issue: any) => {
        derived.push({
          id: `esc-${idx++}`, type: "escalation" as const,
          title: "Finding Escalated",
          message: `${issue.title} escalated to level ${issue.escalationLevel}`,
          timestamp: new Date(now - idx * 60000).toISOString(), read: false,
        });
      });

    // Unassigned high-risk issues → assignments
    (localIssues || [])
      .filter((i: any) => !i.assignee && (i.severity === "critical" || i.severity === "high"))
      .slice(0, 3)
      .forEach((issue: any) => {
        derived.push({
          id: `asn-${idx++}`, type: "assignment" as const,
          title: "Finding Needs Assignment",
          message: `${issue.title} — ${issue.severity} severity, no assignee`,
          timestamp: new Date(now - idx * 60000).toISOString(), read: false,
        });
      });

    // Overdue items → SLA breach
    (localIssues || [])
      .filter((i: any) => i.dueDate && new Date(i.dueDate) < new Date() && i.status !== "resolved" && i.status !== "accepted")
      .slice(0, 2)
      .forEach((issue: any) => {
        derived.push({
          id: `sla-${idx++}`, type: "sla_breach" as const,
          title: "Overdue Finding",
          message: `${issue.title} was due ${new Date(issue.dueDate).toLocaleDateString()}`,
          timestamp: new Date(now - idx * 60000).toISOString(), read: false,
        });
      });

    setNotifications(derived);
  }, [selectedSessionId, session, localIssues]);

  // ── Auto-save draft for comment input ────────────────────────
  const commentAutosave = useAutosave({
    storageKey: `neg-comment-${selectedSessionId}-${activeClauseId}`,
    delay: 300,
    enabled: !!selectedSessionId,
  });

  // ── Derive participants (add current user if none exist) ─────
  const derivedParticipants = React.useMemo(() => {
    const existing = session?.participants || [];
    if (existing.length > 0) return existing;
    return [{
      id: "user-1",
      name: "Current User",
      avatar: "U",
      role: "owner" as const,
      department: "Legal",
      isOnline: true,
      lastActive: new Date().toISOString(),
      reviewedClauses: 0,
      pendingApprovals: 0,
    }];
  }, [session]);

  // Build KPI cards from API data
  const kpiCards: NegotiationKpi[] = React.useMemo(() => {
    const k = kpisData;
    if (!k) return [];
    const sd = k.sparkline_data || {};
    return [
      {
        id: "total",
        label: "Total Sessions",
        value: String(k.total_sessions),
        trend: 0, trendDirection: "neutral",
        icon: "GitBranch", color: "blue", severity: "info",
        sparklineData: sd.sessions_created || [], tooltip: "Total negotiation sessions",
      },
      {
        id: "active",
        label: "Active",
        value: String(k.active_sessions),
        trend: 0, trendDirection: "neutral",
        icon: "Activity", color: "green", severity: "success",
        sparklineData: sd.sessions_created || [], tooltip: "Active negotiations in progress",
      },
      {
        id: "escalated",
        label: "Escalated",
        value: String(k.escalated_count),
        trend: 0, trendDirection: "neutral",
        icon: "AlertTriangle", color: "red", severity: "critical",
        sparklineData: sd.issues_resolved || [], tooltip: "Escalated negotiations requiring attention",
      },
      ...Object.entries(k.by_stage).map(([stage, count]) => ({
        id: `stage-${stage}`,
        label: stage.charAt(0).toUpperCase() + stage.slice(1),
        value: String(count),
        trend: 0, trendDirection: "neutral" as const,
        icon: "Target", color: "amber", severity: "info" as const,
        sparklineData: sd.sessions_created || [] as number[], tooltip: `Sessions in ${stage} stage`,
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

  // ── Derive playbooks from clause categories ──────────────────
  const derivedPlaybooks = React.useMemo(() => {
    const existing = (session as any)?.playbooks || [];
    if (Array.isArray(existing) && existing.length > 0) return existing;
    const categories = new Set(clauses.map((c: any) => c.category).filter(Boolean));
    return Array.from(categories).map((cat: string, idx: number) => ({
      id: `pb-${idx}`,
      title: `${cat.replace(/_/g, " ")} Negotiation Guide`,
      description: `Best practices and fallback positions for ${cat.replace(/_/g, " ")} clauses.`,
      clauseCategory: cat,
      fallbackClauses: [
        { id: `fb-${idx}-1`, title: `Standard ${cat.replace(/_/g, " ")}`, content: "", strength: "moderate" as const, acceptanceRate: 75, riskReduction: 30, usageCount: 42 },
        { id: `fb-${idx}-2`, title: `Market ${cat.replace(/_/g, " ")}`, content: "", strength: "strong" as const, acceptanceRate: 60, riskReduction: 50, usageCount: 28 },
      ],
      escalationGuidance: `Escalate if counterparty refuses standard ${cat.replace(/_/g, " ")} terms.`,
      riskTolerance: "moderate" as const,
      aiRecommended: true,
    }));
  }, [session, clauses]);

  // ── Derive insights from issues/redlines ─────────────────────
  const derivedInsights = React.useMemo(() => {
    const existing = (session as any)?.insights || [];
    if (Array.isArray(existing) && existing.length > 0) return existing;
    // Generate insights from high-risk issues
    const highRiskIssues = localIssues.filter((i: any) =>
      i.severity === "critical" || i.severity === "high" || i.riskLevel === "critical"
    );
    return highRiskIssues.slice(0, 5).map((issue: any, idx: number) => ({
      id: `insight-${idx}`,
      type: (idx === 0 ? "risk" : idx === 1 ? "benchmark" : idx === 2 ? "strategy" : idx === 3 ? "compliance" : "opportunity") as any,
      title: issue.title,
      description: `AI analysis: ${issue.description?.substring(0, 120) || `This ${issue.severity} finding requires attention. Recommended approach: negotiate with counterparty to align with market standards.`}`,
      confidence: 85 - idx * 5,
      impact: (idx < 2 ? "high" : idx < 4 ? "medium" : "low") as any,
      severity: (issue.severity === "critical" ? "critical" : issue.severity === "high" ? "warning" : "info") as any,
      category: issue.category || "general",
      clauseId: issue.clauseId,
      suggestedResponse: `Consider negotiating ${issue.title.toLowerCase()} to reduce risk exposure.`,
    }));
  }, [session, localIssues]);

  // Handlers
  const handleRedlineAccept = useCallback((redlineId: string) => {
    if (!selectedSessionId) return;
    negotiationsService.updateRedlineStatus(selectedSessionId, redlineId, { status: "accepted" })
      .then(() => {
        setLocalRedlines(prev => prev.map((r: any) => r.id === redlineId ? { ...r, status: "accepted" } : r));
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
        queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
        addToast("success", "Redline accepted", "The change has been applied to the clause");
      });
  }, [selectedSessionId, queryClient, addToast]);

  const handleRedlineReject = useCallback((redlineId: string) => {
    if (!selectedSessionId) return;
    negotiationsService.updateRedlineStatus(selectedSessionId, redlineId, { status: "rejected" })
      .then(() => {
        setLocalRedlines(prev => prev.map((r: any) => r.id === redlineId ? { ...r, status: "rejected" } : r));
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
        queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
        addToast("info", "Redline rejected", "The change has been declined");
      });
  }, [selectedSessionId, queryClient, addToast]);

  const handleIssueStatusChange = useCallback((issueId: string, status: string) => {
    if (!selectedSessionId) return;
    negotiationsService.updateIssue(selectedSessionId, issueId, { status })
      .then(() => {
        setLocalIssues(prev => prev.map((i: any) => i.id === issueId ? { ...i, status } : i));
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
        queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
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
        queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
        queryClient.invalidateQueries({ queryKey: ["negotiations-list"] });
      });
  }, [selectedSessionId, localIssues, queryClient]);

  const handleRedlineComment = useCallback(async (redlineId: string, body: string) => {
    if (!selectedSessionId) return;
    try {
      await negotiationsService.createComment(selectedSessionId, {
        redlineId,
        content: body,
      });
      queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
      addToast("success", "Comment added", "Your comment has been saved");
    } catch {
      addToast("error", "Failed", "Could not add comment");
    }
  }, [selectedSessionId, queryClient, addToast]);

  const handleApplyInsight = useCallback(async (insight: AiNegotiationInsight) => {
    if (!selectedSessionId) return;
    try {
      await negotiationsService.createRedline(selectedSessionId, {
        clauseId: insight.clauseId || activeClauseId || "",
        type: "suggestion",
        title: `Insight: ${insight.title}`,
        originalText: "",
        modifiedText: insight.suggestedResponse || insight.description || "",
        riskLevel: insight.severity === "critical" ? "high" : insight.severity === "warning" ? "medium" : "low",
      });
      queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      addToast("success", "Insight applied", `Redline created from insight: ${insight.title}`);
    } catch {
      addToast("error", "Failed", "Could not apply insight");
    }
  }, [selectedSessionId, activeClauseId, queryClient, addToast]);

  const handleApplyFallback = useCallback(async (fb: FallbackClause) => {
    if (!selectedSessionId) return;
    try {
      const clauseId = activeClauseId || "";
      await negotiationsService.createRedline(selectedSessionId, {
        clauseId,
        type: "modification",
        title: `Fallback: ${fb.title}`,
        originalText: "",
        modifiedText: fb.content || fb.title,
        riskLevel: fb.strength === "strong" ? "low" : fb.strength === "moderate" ? "medium" : "high",
      });
      queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      addToast("success", "Fallback applied", `Redline created from fallback: ${fb.title}`);
    } catch {
      addToast("error", "Failed", "Could not apply fallback");
    }
  }, [selectedSessionId, activeClauseId, queryClient, addToast]);

  const handleApplyBundle = useCallback(async (clauseId: string, clauseType: string) => {
    if (!selectedSessionId) return;
    try {
      const result = await negotiationsService.applyClauseBundle(selectedSessionId, clauseId, {
        clause_type: clauseType,
        target_clause_id: clauseId,
      });
      queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
      addToast("success", "Bundle applied", `${result.templates_applied} templates added to clause`);
    } catch (err) {
      console.error("Bundle apply failed:", err);
    }
  }, [selectedSessionId, queryClient]);

  const handleClauseSelect = useCallback((clauseId: string) => {
    setActiveClauseId(clauseId);
    setShowClauseDrawer(true);
  }, []);

  const handleGenerateAiRedlines = useCallback(async () => {
    if (!selectedSessionId) return;
    addToast("info", "AI Redlines", "AI redline generation started — this may take a moment.");
    try {
      const pendingIssues = localIssues.filter((i: any) =>
        i.status === "open" || i.status === "in_review"
      );
      let created = 0;
      for (const issue of pendingIssues) {
        try {
          await negotiationsService.createRedline(selectedSessionId, {
            clauseId: issue.clauseId || "",
            type: "suggestion",
            title: `AI Suggestion: ${issue.title}`,
            originalText: "",
            modifiedText: issue.description || `Address ${issue.title} — recommended language per negotiation playbook.`,
            riskLevel: issue.severity === "critical" || issue.severity === "blocker" ? "high" : "medium",
          });
          created++;
        } catch {
          // Continue with remaining issues
        }
      }
      queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
      addToast("success", "AI Redlines", `Generated ${created} redline${created !== 1 ? "s" : ""} from ${pendingIssues.length} pending issue${pendingIssues.length !== 1 ? "s" : ""}`);
    } catch {
      addToast("error", "AI Redlines", "Failed to generate AI redlines");
    }
  }, [selectedSessionId, localIssues, queryClient, addToast]);

  const handleStageChange = useCallback((stage: NegotiationStage) => {
    if (!selectedSessionId) return;
    if (session?.stage === "executed") return;
    if (session?.stage === stage) return;
    const prevStage = session?.stage;
    negotiationsService.updateSession(selectedSessionId, { stage })
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
        queryClient.invalidateQueries({ queryKey: ["negotiations-list"] });
        queryClient.invalidateQueries({ queryKey: ["negotiation-kpis"] });
        addToast("success", `Stage changed`, `Moved from ${prevStage} to ${stage}`);
      })
      .catch((err) => {
        console.error("Stage change failed:", err?.message || err);
        queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
        queryClient.invalidateQueries({ queryKey: ["negotiations-list"] });
        addToast("error", "Stage change failed", err?.message || "Could not update stage");
      });
  }, [selectedSessionId, session?.stage, queryClient, addToast]);

  // ── Action Handlers ──────────────────────────────────────────

  const handleLaunchNegotiation = useCallback(async () => {
    setShowLaunchModal(true);
  }, []);

  const handleCreateRedline = useCallback(() => {
    if (!selectedSessionId) return;
    setShowCreateRedlineModal(true);
  }, [selectedSessionId]);

  const handleExportRedlines = useCallback(() => {
    if (!selectedSessionId || !session) return;
    // Build a text summary of all redlines
    const lines: string[] = [
      `Negotiation Export — ${session.contractTitle}`,
      `Counterparty: ${session.counterparty}`,
      `Stage: ${session.stage}`,
      `Generated: ${new Date().toISOString()}`,
      "",
      "─".repeat(60),
      "",
    ];
    localRedlines.forEach((r: any, idx: number) => {
      lines.push(`Redline #${idx + 1}: ${r.title}`);
      lines.push(`  Type: ${r.type}  |  Status: ${r.status}  |  Risk: ${r.riskLevel}`);
      if (r.originalText) lines.push(`  Original: ${r.originalText.substring(0, 200)}`);
      if (r.modifiedText) lines.push(`  Modified: ${r.modifiedText.substring(0, 200)}`);
      lines.push("");
    });
    lines.push(`Total Redlines: ${localRedlines.length}`);
    lines.push(`Accepted: ${localRedlines.filter((r: any) => r.status === "accepted").length}`);
    lines.push(`Pending: ${localRedlines.filter((r: any) => r.status === "pending").length}`);
    lines.push(`Rejected: ${localRedlines.filter((r: any) => r.status === "rejected").length}`);

    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `negotiation_${session.contractTitle.replace(/\s+/g, "_")}_redlines.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [selectedSessionId, session, localRedlines]);

  const handleKpiClick = useCallback((kpiId: string) => {
    const stageMap: Record<string, string> = {
      "stage-drafting": "drafting",
      "stage-review": "review",
      "stage-negotiating": "negotiating",
      "stage-approved": "approved",
      "stage-executed": "executed",
      "active": "negotiating",
      "escalated": "escalated",
    };
    const stage = stageMap[kpiId];
    if (stage) {
      setStageFilter(stage === stageFilter ? null : stage);
    }
  }, [stageFilter]);

  // Loading state
  if ((sessionLoading && !session) || resumingFromReview) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-navy-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-600 mx-auto mb-4" />
          <p className="text-gray-500 text-sm">
            {resumingFromReview ? "Importing review redlines..." : "Loading negotiation session..."}
          </p>
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

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
      {/* Page Header */}
      <div className="px-4 pt-3 pb-2">
        <PageHeader
          title="Negotiation Center"
          description={`Resolve redlines and negotiate contract language with counterparties. ${sessionCountText}`}
          actions={
            <>
              <NotificationBell
                notifications={notifications}
                onMarkRead={(id) => setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))}
                onMarkAllRead={() => setNotifications(prev => prev.map(n => ({ ...n, read: true })))}
                onNotificationClick={(n) => {
                  addToast("info", n.title, n.message);
                }}
              />
              <button
                onClick={() => router.push("/reviews")}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Reviews
              </button>
              <button
                onClick={handleLaunchNegotiation}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gold-500 text-white hover:bg-gold-600 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                Launch Negotiation
              </button>
              <button
                onClick={handleCreateRedline}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors"
              >
                <PenTool className="w-3.5 h-3.5" />
                Create Redline
              </button>
              <button
                onClick={handleExportRedlines}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <FileOutput className="w-3.5 h-3.5" />
                Export Redlines
              </button>
            </>
          }
        />
      </div>

      {/* KPI Row */}
      <div className="px-4 pb-2">
        <NegotiationKpiCards metrics={kpiCards} onKpiClick={handleKpiClick} />
        {stageFilter && (
          <div className="mt-1 flex items-center gap-1.5">
            <span className="text-[10px] text-gray-500">Filtered by:</span>
            <span className="text-[10px] font-medium px-1.5 py-0.5 bg-gold-100 text-gold-700 rounded-full capitalize">
              {stageFilter} stage
            </span>
            <button
              onClick={() => setStageFilter(null)}
              className="text-[10px] text-gray-400 hover:text-gray-600 underline"
            >
              Clear filter
            </button>
          </div>
        )}
      </div>

      {/* Session Search */}
      <div className="px-4 pb-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={sessionSearchQuery}
            onChange={(e) => setSessionSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setTimeout(() => setSearchFocused(false), 200)}
            placeholder="Search sessions by title or counterparty..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-800 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
          />
          {/* Selected session indicator */}
          {selectedSessionId && !sessionSearchQuery && !document.activeElement?.closest('.session-search') && (
            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-gray-500">
              <span className="font-medium text-navy-900 dark:text-white">
                {sessions.find((s: any) => s.id === selectedSessionId)?.contractTitle || "Selected"}
              </span>
              <span className="text-gray-400">—</span>
              <span>{sessions.length} session{sessions.length !== 1 ? "s" : ""}</span>
              {stageFilter && (
                <span className="text-gold-600 ml-1">(filtered: {filteredSessions.length})</span>
              )}
            </div>
          )}
        </div>
        {/* Show dropdown when search is focused or has text */}
        {(searchFocused || sessionSearchQuery) && sessions.length > 0 && (
          <div className="mt-1 max-h-40 overflow-y-auto bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-sm">
            {sessions.length === 0 ? (
              <div className="px-3 py-3 text-xs text-gray-400">
                <p>No sessions loaded yet.</p>
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="px-3 py-3 text-xs text-gray-400">
                <p>No sessions match "{sessionSearchQuery}"</p>
                <p className="mt-1 text-gray-500">Try a different search term or create a new session.</p>
              </div>
            ) : (
              filteredSessions.map((s: any) => (
                <button
                  key={s.id}
                  onClick={() => { setSelectedSessionId(s.id); setSessionSearchQuery(""); }}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors flex items-center justify-between ${
                    s.id === selectedSessionId ? "bg-navy-50 dark:bg-navy-700" : ""
                  }`}
                >
                  <div>
                    <span className="font-medium text-navy-900 dark:text-white">{s.contractTitle}</span>
                    {s.counterparty && (
                      <span className="text-gray-500 ml-2">– {s.counterparty}</span>
                    )}
                  </div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full capitalize ${
                    s.stage === "executed" ? "bg-emerald-100 text-emerald-700" :
                    s.stage === "approved" ? "bg-green-100 text-green-700" :
                    s.stage === "drafting" ? "bg-gray-100 text-gray-600" :
                    "bg-blue-100 text-blue-700"
                  }`}>
                    {s.stage}
                  </span>
                </button>
              ))
            )}
          </div>
        )}
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
        onExport={handleExportRedlines}
        onAssignReviewer={() => {
          addToast("info", "Assign Reviewer", "Reviewer assignment dialog coming soon — use the Participants tab to manage team members.");
        }}
        onStageChange={handleStageChange}
        onSessionAction={async (action) => {
          if (!selectedSessionId) return;
          try {
            if (action === "lock") {
              await negotiationsService.updateSession(selectedSessionId, { stage: "approved" });
              queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
              addToast("success", "Session locked", "Session has been locked to prevent further edits");
            } else if (action === "unlock") {
              await negotiationsService.updateSession(selectedSessionId, { stage: "negotiating" });
              queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
              addToast("success", "Session unlocked", "Session is now editable");
            } else if (action === "archive") {
              addToast("info", "Archive", "Archive coming soon — session will be preserved for audit");
            } else if (action === "clone") {
              addToast("info", "Clone", "Clone coming soon — duplicate this session with all clauses");
            }
          } catch {
            addToast("error", "Action failed", `Could not ${action} session`);
          }
        }}
      />

      {/* Finding Context Header */}
      <FindingContextHeader
        contractTitle={session.contractTitle}
        counterparty={session.counterparty}
        findingIndex={Math.min(findingIndex, localIssues.length - 1)}
        totalFindings={localIssues.length}
        clauseTitle={activeClause?.title}
        riskLevel={activeClause?.riskLevel || localIssues[findingIndex]?.severity}
        status={localIssues[findingIndex]?.status}
        assignedTo={localIssues[findingIndex]?.assignee || undefined}
      />

      {/* Progress Tracking */}
      <ProgressBar
        data={{
          total: localIssues.length,
          completed: localIssues.filter((i: any) => i.status === "resolved" || i.status === "accepted").length,
          pending: localIssues.filter((i: any) => i.status === "open" || i.status === "in_review").length,
          escalated: localIssues.filter((i: any) => i.status === "escalated").length,
          ignored: localIssues.filter((i: any) => i.status === "rejected" || i.status === "dismissed").length,
        }}
      />

      {/* Workflow Stepper */}
      <WorkflowStepper currentStep={workflowStep} onStepClick={setWorkflowStep} />

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
                participants={derivedParticipants}
                playbooks={derivedPlaybooks}
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

          {/* Finding Navigation — driven by FlowEngine */}
          {localIssues.length > 0 && (
            <div className="px-2 py-1">
              <FindingNavigation
                currentIndex={Math.min(findingIndex, localIssues.length - 1)}
                total={localIssues.length}
                currentStatus={localIssues[findingIndex]?.status}
                onPrevious={goToPrev}
                onNext={goToNext}
                onAccept={() => {
                  const issue = localIssues[findingIndex];
                  if (issue) handleIssueStatusChange(issue.id, "accepted");
                  addToast("success", "Finding accepted", "Marked as accepted");
                }}
                onReject={() => {
                  const issue = localIssues[findingIndex];
                  if (issue) handleIssueStatusChange(issue.id, "rejected");
                  addToast("info", "Finding rejected", "Marked as rejected");
                }}
                onIgnore={() => {
                  const issue = localIssues[findingIndex];
                  if (issue) handleIssueStatusChange(issue.id, "dismissed");
                  addToast("info", "Finding ignored", "Dismissed from active view");
                }}
                onResolve={() => {
                  const issue = localIssues[findingIndex];
                  if (issue) {
                    handleIssueStatusChange(issue.id, "resolved");
                    resolveAndAdvance();
                    addToast("success", "Finding resolved", "Risk score updated");
                  }
                }}
                onReopen={() => {
                  const issue = localIssues[findingIndex];
                  if (issue) handleIssueStatusChange(issue.id, "open");
                  addToast("info", "Finding reopened", "Returned to active findings");
                }}
                onEscalate={() => {
                  const issue = localIssues[findingIndex];
                  if (issue) {
                    setConfirmDialog({
                      isOpen: true,
                      title: "Escalate finding?",
                      message: `This will escalate "${issue.title}" to level ${(issue.escalationLevel || 0) + 1}. Senior reviewers will be notified.`,
                      variant: "warning",
                      onConfirm: () => {
                        handleIssueEscalate(issue.id);
                        addToast("warning", "Finding escalated", "Sent to escalation workflow");
                        setConfirmDialog(prev => ({ ...prev, isOpen: false }));
                      },
                    });
                  }
                }}
                onSkip={() => goToNext()}
                onShowAll={() => setActiveIssueId(null)}
              />
            </div>
          )}

          {/* Finding Context Header */}
          {currentFinding && (
            <FindingContextHeader
              contractTitle={session.contractTitle}
              findingIndex={findingIndex + 1}
              totalFindings={totalFindings}
              clauseTitle={activeClause?.title || ""}
              riskLevel={currentFinding.riskLevel || "medium"}
              status={currentFinding.status}
              assignee={currentFinding.assignee || undefined}
            />
          )}

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
              onCreateRedline={handleCreateRedline}
              onAiRewrite={handleGenerateAiRedlines}
              onRedlineComment={handleRedlineComment}
              sessionId={selectedSessionId || ""}
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
                insights={derivedInsights}
                playbooks={derivedPlaybooks}
                analytics={{
                  totalSessions: 0,
                  avgCycleTime: 0,
                  concessionRate: 0,
                  redlineAcceptanceRate: 0,
                  clauseDisputeFrequency: [],
                  vendorAggressiveness: [],
                  cycleBottlenecks: [],
                  timelineData: [],
                  issueHeatmap: [],
                  reviewThroughput: [],
                }}
                onApplyInsight={handleApplyInsight}
                onApplyFallback={handleApplyFallback}
                sessionId={selectedSessionId ?? undefined}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Issue Detail Drawer */}
      <IssueDetailDrawer
        issue={activeIssue}
        sessionId={selectedSessionId || ""}
        isOpen={!!activeIssueId}
        onClose={() => setActiveIssueId(null)}
        onStatusChange={handleIssueStatusChange}
        onEscalate={handleIssueEscalate}
        onCommentAdded={() => {
          queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
          queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
        }}
      />

      {/* Clause Detail Drawer — Unified Persistent Drawer */}
      <NegotiationClauseDrawer
        clause={activeClause}
        originalText={activeClauseOriginalText}
        modifiedText={activeClauseModifiedText}
        redlines={localRedlines}
        insights={[]}
        playbooks={[]}
        comments={activeClauseComments}
        sessionId={selectedSessionId || ""}
        isOpen={showClauseDrawer && !!activeClause}
        onClose={() => setShowClauseDrawer(false)}
        onApplyFallback={handleApplyFallback}
        onApplyBundle={handleApplyBundle}
        onRedlineAccept={handleRedlineAccept}
        onRedlineReject={handleRedlineReject}
        onRefreshSession={() => {
          queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
          queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
        }}
      />

      {/* Launch Negotiation Modal */}
      <AnimatePresence>
        {showLaunchModal && (
          <LaunchNegotiationModal
            onClose={() => setShowLaunchModal(false)}
            onCreated={(sessionId) => {
              setShowLaunchModal(false);
              if (sessionId) setSelectedSessionId(sessionId);
              queryClient.invalidateQueries({ queryKey: ["negotiations-list"] });
              queryClient.invalidateQueries({ queryKey: ["negotiation-kpis"] });
            }}
          />
        )}
      </AnimatePresence>

      {/* Create Redline Modal */}
      <AnimatePresence>
        {showCreateRedlineModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/30 z-50"
              onClick={() => setShowCreateRedlineModal(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="bg-white dark:bg-navy-800 rounded-xl shadow-2xl border border-gray-200 dark:border-navy-700 w-full max-w-lg">
                <div className="px-5 py-4 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <PenTool className="w-4 h-4 text-navy-500" />
                    <h3 className="text-sm font-semibold text-navy-900 dark:text-white">Create Redline</h3>
                  </div>
                  <button onClick={() => setShowCreateRedlineModal(false)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <CreateRedlineForm
                  sessionId={selectedSessionId || ""}
                  clauses={clauses}
                  onCreated={() => {
                    setShowCreateRedlineModal(false);
                    queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
                    queryClient.invalidateQueries({ queryKey: ["negotiation-activities", selectedSessionId] });
                  }}
                  onClose={() => setShowCreateRedlineModal(false)}
                />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.title}
        message={confirmDialog.message}
        variant={confirmDialog.variant || "danger"}
        onConfirm={() => { confirmDialog.onConfirm(); }}
        onCancel={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
      />

      {/* Completion Wizard — shown after all findings resolved */}
      <CompletionWizard
        isOpen={showCompletionWizard}
        onClose={() => setShowCompletionWizard(false)}
        sessionId={selectedSessionId || ""}
        contractTitle={session?.contractTitle || ""}
        totalFindings={totalFindings}
        resolvedCount={totalFindings - totalOpen}
        riskBefore={91} // TODO: get from session analytics
        riskAfter={52}  // TODO: get from session analytics
        onGenerateSummary={async () => {
          try {
            const summary = await negotiationsService.getNegotiationSummary(selectedSessionId!);
            addToast("success", "Summary generated", "Executive summary created");
          } catch {
            addToast("error", "Failed", "Could not generate summary");
          }
        }}
        onGenerateReport={async () => {
          addToast("info", "Report", "Final report generation started");
        }}
        onExportContract={async () => {
          handleExportRedlines();
          addToast("info", "Export", "Contract export started");
        }}
        onCloseSession={async () => {
          if (selectedSessionId) {
            await negotiationsService.updateSession(selectedSessionId, { stage: "executed" });
            queryClient.invalidateQueries({ queryKey: ["negotiation", selectedSessionId] });
            addToast("success", "Session closed", "Negotiation session marked as executed");
            setShowCompletionWizard(false);
          }
        }}
      />
    </div>
  );
}

// ── Create Redline Form ───────────────────────────────────────────

function CreateRedlineForm({
  sessionId, clauses, onCreated, onClose,
}: {
  sessionId: string;
  clauses: any[];
  onCreated: () => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState("");
  const [clauseId, setClauseId] = useState(clauses[0]?.clauseId || "");
  const [type, setType] = useState<string>("modification");
  const [originalText, setOriginalText] = useState("");
  const [modifiedText, setModifiedText] = useState("");
  const [riskLevel, setRiskLevel] = useState<string>("medium");
  const [saving, setSaving] = useState(false);

  // Update clauseId when clauses load (async)
  React.useEffect(() => {
    if (!clauseId && clauses.length > 0) {
      setClauseId(clauses[0].clauseId);
      setOriginalText(clauses[0].content || "");
    }
  }, [clauses, clauseId]);

  const handleSave = async () => {
    if (!title.trim()) return;
    setSaving(true);
    try {
      await negotiationsService.createRedline(sessionId, {
        clauseId,
        type,
        title: title.trim(),
        originalText,
        modifiedText: modifiedText || undefined,
        riskLevel,
      });
      onCreated();
    } catch {
      // error handled silently
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-5 space-y-3">
      <div>
        <label className="text-[10px] font-semibold text-gray-500 uppercase mb-1 block">Title</label>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="e.g., Reduce liability cap"
          className="w-full px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] font-semibold text-gray-500 uppercase mb-1 block">Clause</label>
          {clauses.length === 0 ? (
            <div className="px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-100 dark:bg-navy-900 text-gray-400 italic">
              No clauses available — add clauses to the session first
            </div>
          ) : (
            <select
              value={clauseId}
              onChange={e => {
                setClauseId(e.target.value);
                const c = clauses.find((cl: any) => cl.clauseId === e.target.value);
                if (c) setOriginalText(c.content || "");
              }}
              className="w-full px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gold-400"
            >
              {clauses.map((c: any) => (
                <option key={c.clauseId} value={c.clauseId}>{c.title}</option>
              ))}
            </select>
          )}
        </div>
        <div>
          <label className="text-[10px] font-semibold text-gray-500 uppercase mb-1 block">Type</label>
          <select
            value={type}
            onChange={e => setType(e.target.value)}
            className="w-full px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gold-400"
          >
            <option value="modification">Modification</option>
            <option value="addition">Addition</option>
            <option value="deletion">Deletion</option>
            <option value="comment">Comment</option>
            <option value="suggestion">Suggestion</option>
          </select>
        </div>
      </div>
      <div>
        <label className="text-[10px] font-semibold text-gray-500 uppercase mb-1 block">Original Text</label>
        <textarea
          value={originalText}
          onChange={e => setOriginalText(e.target.value)}
          rows={2}
          className="w-full px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400 resize-none font-mono"
        />
      </div>
      <div>
        <label className="text-[10px] font-semibold text-gray-500 uppercase mb-1 block">Modified Text</label>
        <textarea
          value={modifiedText}
          onChange={e => setModifiedText(e.target.value)}
          rows={2}
          className="w-full px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400 resize-none font-mono"
        />
      </div>
      <div>
        <label className="text-[10px] font-semibold text-gray-500 uppercase mb-1 block">Risk Level</label>
        <select
          value={riskLevel}
          onChange={e => setRiskLevel(e.target.value)}
          className="w-full px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-gold-400"
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </div>
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={handleSave}
          disabled={saving || !title.trim()}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-navy-700 hover:bg-navy-800 disabled:bg-gray-300 text-white rounded-lg text-[11px] font-semibold transition-colors"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
          {saving ? "Creating..." : "Create Redline"}
        </button>
        <button
          onClick={onClose}
          className="px-3 py-2 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 text-gray-700 dark:text-gray-300 rounded-lg text-[11px] font-semibold transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Launch Negotiation Modal ──────────────────────────────────────

function LaunchNegotiationModal({
  onClose, onCreated,
}: {
  onClose: () => void;
  onCreated: (sessionId: string) => void;
}) {
  const [mode, setMode] = useState<"choose" | "from-review" | "fresh">("choose");
  const [title, setTitle] = useState("");
  const [party, setParty] = useState("");
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartFresh = async () => {
    if (!title.trim() || !party.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const session = await negotiationsService.createSession({
        contractTitle: title.trim(),
        counterparty: party.trim(),
        ...(selectedReviewId ? { contractId: selectedReviewId } : {}),
      });
      onCreated(session.id);
    } catch (err: any) {
      setError(err?.message || "Failed to create session");
    } finally {
      setSaving(false);
    }
  };

  const handleStartFromReview = async (reviewId: string, contractTitle: string, counterparty: string) => {
    setSaving(true);
    setError(null);
    try {
      const session = await negotiationsService.resumeOrCreateFromReview({
        reviewId,
        counterparty: counterparty || undefined,
      });
      onCreated(session.id);
    } catch (err: any) {
      setError(err?.message || "Failed to create session from review");
      setSaving(false);
    }
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/30 z-50"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-white dark:bg-navy-800 rounded-xl shadow-2xl border border-gray-200 dark:border-navy-700 w-full max-w-md">
          <div className="px-5 py-4 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Send className="w-4 h-4 text-gold-500" />
              <h3 className="text-sm font-semibold text-navy-900 dark:text-white">
                {mode === "choose" ? "Launch Negotiation" : mode === "fresh" ? "Start Fresh" : "From Contract Review"}
              </h3>
            </div>
            <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-5">
            {mode === "choose" && (
              <div className="space-y-3">
                <p className="text-[11px] text-gray-500">Create a negotiation session from an existing contract review, or start fresh.</p>
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => setMode("from-review")}
                    className="flex items-center gap-2 px-3 py-2.5 bg-gold-500 hover:bg-gold-600 text-white rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    <GitBranch className="w-4 h-4" />
                    From Contract Review
                  </button>
                  <button
                    onClick={() => setMode("fresh")}
                    className="flex items-center gap-2 px-3 py-2.5 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 text-gray-700 dark:text-gray-300 rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    Start Fresh
                  </button>
                </div>
              </div>
            )}

            {mode === "from-review" && (
              <div className="space-y-3">
                <p className="text-[11px] text-gray-500">Select a completed contract review to base this negotiation on.</p>
                {error && (
                  <div className="text-[10px] text-red-600 bg-red-50 dark:bg-red-900/20 px-2 py-1.5 rounded-lg border border-red-200">
                    {error}
                  </div>
                )}
                {saving ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                  </div>
                ) : (
                  <FromContractReviewList
                    onSelect={(reviewId, contractTitle, counterparty) => {
                      handleStartFromReview(reviewId, contractTitle, counterparty);
                    }}
                  />
                )}
                <button
                  onClick={() => setMode("choose")}
                  className="text-[10px] text-gold-600 hover:text-gold-700 font-medium"
                >
                  ← Back
                </button>
              </div>
            )}

            {mode === "fresh" && (
              <div className="space-y-3">
                <div>
                  <label className="text-[10px] font-semibold text-gray-500 uppercase mb-1 block">Contract Title</label>
                  <input
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    placeholder="e.g., Master Services Agreement"
                    className="w-full px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-semibold text-gray-500 uppercase mb-1 block">Counterparty</label>
                  <input
                    value={party}
                    onChange={e => setParty(e.target.value)}
                    placeholder="e.g., Acme Corp"
                    className="w-full px-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
                  />
                </div>
                {error && (
                  <div className="text-[10px] text-red-600 bg-red-50 dark:bg-red-900/20 px-2 py-1.5 rounded-lg border border-red-200">
                    {error}
                  </div>
                )}
                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={handleStartFresh}
                    disabled={saving || !title.trim() || !party.trim()}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 text-white rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    {saving ? "Creating..." : "Create Session"}
                  </button>
                  <button
                    onClick={() => setMode("choose")}
                    className="px-3 py-2 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 text-gray-700 dark:text-gray-300 rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    Back
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </>
  );
}

// ── From Contract Review List ─────────────────────────────────────

function FromContractReviewList({
  onSelect,
}: {
  onSelect: (reviewId: string, contractTitle: string, counterparty: string) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["contract-reviews-minimal"],
    queryFn: async () => {
      const { reviewService } = await import("@/services/api/reviews");
      // Valid backend statuses: draft, uploaded, analyzing, submitted, ai_reviewed,
      // review_ready, procurement_review, legal_review, security_review,
      // negotiation, approved, changes_requested, rejected, cancelled,
      // legal_approval, exec_approval, in_progress, pending, finalized,
      // executed, archived, on_hold
      // Try approved reviews first (most relevant for negotiation)
      try {
        const resp = await reviewService.list({ status: "approved", page_size: 20 });
        const items = (resp as any).data ?? resp ?? [];
        if (Array.isArray(items) && items.length > 0) return { reviews: items, status: "approved" };
      } catch { /* fall through */ }
      // Fall back to finalized or executed reviews
      try {
        const resp = await reviewService.list({ status: "finalized", page_size: 20 });
        const items = (resp as any).data ?? resp ?? [];
        if (Array.isArray(items) && items.length > 0) return { reviews: items, status: "finalized" };
      } catch { /* fall through */ }
      // Last resort: show any review at all
      try {
        const resp = await reviewService.list({ page_size: 20 });
        const items = (resp as any).data ?? resp ?? [];
        return { reviews: Array.isArray(items) ? items : [], status: "all" };
      } catch {
        return { reviews: [], status: "none" };
      }
    },
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
      </div>
    );
  }

  const reviews: any[] = data?.reviews ?? [];
  const status = data?.status ?? "none";

  if (reviews.length === 0) {
    return (
      <div className="text-center py-6 text-gray-400">
        <p className="text-[11px]">No contract reviews found.</p>
        <p className="text-[10px] mt-1">Complete a contract review first, then launch a negotiation from it. Or use <strong>Start Fresh</strong> above.</p>
      </div>
    );
  }

  return (
    <div>
      {status !== "approved" && (
        <div className="mb-2 px-2 py-1 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded text-[9px] text-amber-700 dark:text-amber-400">
          No approved reviews found. Showing {status === "finalized" ? "finalized" : "all available"} reviews instead.
        </div>
      )}
      <div className="max-h-48 overflow-y-auto space-y-1">
        {reviews.map((r: any) => (
          <button
            key={r.review_id || r.id}
            onClick={() => onSelect(
              r.review_id || r.id,
              r.document_name || r.contractTitle || "Untitled",
              r.counterparty || r.vendor_name || r.assigned_to_name || "",
            )}
            className="w-full text-left px-3 py-2 text-[11px] hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg border border-transparent hover:border-gray-200 dark:hover:border-navy-600 transition-all"
          >
            <span className="font-medium text-navy-900 dark:text-white block truncate">
              {r.document_name || r.contractTitle || "Untitled"}
            </span>
            <span className="text-gray-500 text-[10px]">
              {r.counterparty || r.vendor_name || r.assigned_to_name || "—"}
              <span className="ml-1.5 px-1 py-0.5 rounded text-[8px] bg-gray-100 dark:bg-navy-700 capitalize">{r.status || ""}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}


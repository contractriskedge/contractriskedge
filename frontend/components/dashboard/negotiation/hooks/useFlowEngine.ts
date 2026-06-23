"use client";

import { useState, useCallback, useMemo, useEffect } from "react";

// ── Types ────────────────────────────────────────────────────────

export interface FindingItem {
  id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  riskLevel?: string;
  assignee?: string | null;
  dueDate?: string | null;
  escalationLevel?: number;
}

export type FlowStep =
  | "open"
  | "review"
  | "coach"
  | "rewrite"
  | "vote"
  | "resolve"
  | "complete";

export interface FlowEngineState {
  /** Current finding index */
  findingIndex: number;
  /** Total unresolved findings */
  totalOpen: number;
  /** Total findings */
  totalFindings: number;
  /** Current workflow step */
  currentStep: FlowStep;
  /** Whether all findings are resolved */
  isComplete: boolean;
  /** Progress percentage */
  progressPercent: number;
  /** Current finding */
  currentFinding: FindingItem | null;
  /** Filtered finding list */
  findings: FindingItem[];
}

export interface FlowEngineActions {
  /** Go to next unresolved finding (auto-advance after resolve) */
  goToNext: () => void;
  /** Go to previous finding */
  goToPrev: () => void;
  /** Jump to a specific finding index */
  goToIndex: (index: number) => void;
  /** Mark current finding resolved and auto-advance */
  resolveAndAdvance: () => void;
  /** Set the workflow step */
  setStep: (step: FlowStep) => void;
  /** Reset to first finding */
  reset: () => void;
  /** Get the next unresolved finding index (for auto-advance target) */
  getNextUnresolvedIndex: (fromIndex?: number) => number;
}

// ── Severity weight for sorting ──────────────────────────────────

const SEVERITY_WEIGHT: Record<string, number> = {
  blocker: 5,
  critical: 4,
  high: 3,
  major: 3,
  medium: 2,
  minor: 1,
  low: 1,
  info: 0,
};

function getSeverityWeight(severity: string): number {
  return SEVERITY_WEIGHT[severity.toLowerCase()] ?? 0;
}

// ── Hook ─────────────────────────────────────────────────────────

export function useFlowEngine(
  findings: FindingItem[],
  initialIndex?: number,
): FlowEngineState & FlowEngineActions {
  // Sort findings: highest severity first, unresolved before resolved
  const sortedFindings = useMemo(() => {
    return [...findings].sort((a, b) => {
      // Unresolved first
      const aResolved = a.status === "resolved" || a.status === "accepted" || a.status === "closed";
      const bResolved = b.status === "resolved" || b.status === "accepted" || b.status === "closed";
      if (aResolved && !bResolved) return 1;
      if (!aResolved && bResolved) return -1;
      // Then by severity (highest first)
      return getSeverityWeight(b.severity) - getSeverityWeight(a.severity);
    });
  }, [findings]);

  // Find the first unresolved finding (highest severity)
  const firstUnresolvedIndex = useMemo(() => {
    return sortedFindings.findIndex(
      (f) => f.status !== "resolved" && f.status !== "accepted" && f.status !== "closed",
    );
  }, [sortedFindings]);

  const [findingIndex, setFindingIndex] = useState(
    initialIndex ?? (firstUnresolvedIndex >= 0 ? firstUnresolvedIndex : 0),
  );
  const [currentStep, setCurrentStep] = useState<FlowStep>("open");

  // Reset finding index when findings list changes significantly
  useEffect(() => {
    if (firstUnresolvedIndex >= 0 && findingIndex >= sortedFindings.length) {
      setFindingIndex(firstUnresolvedIndex);
    }
  }, [sortedFindings.length, firstUnresolvedIndex, findingIndex]);

  const totalFindings = sortedFindings.length;
  const resolvedCount = sortedFindings.filter(
    (f) => f.status === "resolved" || f.status === "accepted" || f.status === "closed",
  ).length;
  const totalOpen = totalFindings - resolvedCount;
  const isComplete = totalOpen === 0 && totalFindings > 0;
  const progressPercent = totalFindings > 0 ? Math.round((resolvedCount / totalFindings) * 100) : 0;

  const currentFinding = sortedFindings[findingIndex] ?? null;

  const getNextUnresolvedIndex = useCallback(
    (fromIndex?: number) => {
      const start = (fromIndex ?? findingIndex) + 1;
      for (let i = start; i < sortedFindings.length; i++) {
        const f = sortedFindings[i];
        if (f.status !== "resolved" && f.status !== "accepted" && f.status !== "closed") {
          return i;
        }
      }
      return -1; // No more unresolved
    },
    [sortedFindings, findingIndex],
  );

  const goToNext = useCallback(() => {
    setFindingIndex((prev) => Math.min(prev + 1, sortedFindings.length - 1));
  }, [sortedFindings.length]);

  const goToPrev = useCallback(() => {
    setFindingIndex((prev) => Math.max(prev - 1, 0));
  }, []);

  const goToIndex = useCallback((index: number) => {
    setFindingIndex(Math.max(0, Math.min(index, sortedFindings.length - 1)));
  }, [sortedFindings.length]);

  const resolveAndAdvance = useCallback(() => {
    const nextIdx = getNextUnresolvedIndex();
    if (nextIdx >= 0) {
      setFindingIndex(nextIdx);
      setCurrentStep("open");
    } else {
      // All resolved — move to complete
      setCurrentStep("complete");
    }
  }, [getNextUnresolvedIndex]);

  const reset = useCallback(() => {
    setFindingIndex(firstUnresolvedIndex >= 0 ? firstUnresolvedIndex : 0);
    setCurrentStep("open");
  }, [firstUnresolvedIndex]);

  return {
    // State
    findingIndex,
    totalOpen,
    totalFindings,
    currentStep,
    isComplete,
    progressPercent,
    currentFinding,
    findings: sortedFindings,
    // Actions
    goToNext,
    goToPrev,
    goToIndex,
    resolveAndAdvance,
    setStep: setCurrentStep,
    reset,
    getNextUnresolvedIndex,
  };
}

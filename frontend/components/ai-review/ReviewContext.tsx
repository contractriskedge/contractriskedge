/**
 * Enterprise AI Review Platform — unified review context.
 *
 * Centralized state management across all sections.
 * Auto-selects findings tab and highest-priority finding on review load.
 */

"use client";

import React, { createContext, useContext, useCallback, useMemo, useState, useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { ReviewSummary, Finding, ReviewSection } from "./types";
import {
  useReviews,
  useReview,
  useFindings,
  usePolicyViolations,
  useMissingClauses,
  useRecommendations,
  useWorkflow,
  useActivity,
  useComments,
} from "./hooks";
import { loadRedlineUiState, saveRedlineUiState } from "@/lib/redlineUiState";

// ── Context Shape ───────────────────────────────────────────────────────────

interface ReviewContextValue {
  selectedReviewId: string | null;
  selectReview: (id: string | null) => void;

  reviews: ReviewSummary[];
  selectedReview: ReviewSummary | null;
  findings: Finding[];
  policyViolations: ReturnType<typeof usePolicyViolations>["data"];
  missingClauses: ReturnType<typeof useMissingClauses>["data"];
  recommendations: ReturnType<typeof useRecommendations>["data"];
  workflow: ReturnType<typeof useWorkflow>["data"];
  activity: ReturnType<typeof useActivity>["data"];
  comments: ReturnType<typeof useComments>["data"];

  isReviewsLoading: boolean;
  isReviewLoading: boolean;
  isFindingsLoading: boolean;
  isPolicyLoading: boolean;
  isRecommendationsLoading: boolean;
  isWorkflowLoading: boolean;
  isActivityLoading: boolean;

  activeSection: ReviewSection;
  setActiveSection: (section: ReviewSection) => void;
  selectedFindingId: string | null;
  setSelectedFindingId: (id: string | null) => void;
  expandedFindingId: string | null;
  setExpandedFindingId: (id: string | null) => void;
  showLeftPanel: boolean;
  setShowLeftPanel: React.Dispatch<React.SetStateAction<boolean>>;
  showRightPanel: boolean;
  setShowRightPanel: React.Dispatch<React.SetStateAction<boolean>>;

  /** Persisted across tab switches (Findings ↔ Redline) for the active review */
  selectedRedlineId: string | null;
  setSelectedRedlineId: (id: string | null) => void;
  redlineScrollTop: number;
  setRedlineScrollTop: React.Dispatch<React.SetStateAction<number>>;
  redlineStatusFilter: string;
  setRedlineStatusFilter: React.Dispatch<React.SetStateAction<string>>;

  error: string | null;
}

const ReviewContext = createContext<ReviewContextValue | null>(null);

// ── Priority order for auto-selecting findings ──────────────────────────────

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

function findHighestPriorityFinding(findings: Finding[]): Finding | null {
  if (findings.length === 0) return null;

  // 1. Critical unresolved finding
  const critical = findings.find(f => f.severity === "critical" && f.status === "open");
  if (critical) return critical;

  // 2. Highest severity unresolved finding
  const unresolved = findings
    .filter(f => f.status === "open")
    .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity));
  if (unresolved.length > 0) return unresolved[0];

  // 3. Newest finding
  const sorted = [...findings].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  return sorted[0];
}

// ── Provider ────────────────────────────────────────────────────────────────

interface ReviewContextProviderProps {
  children: React.ReactNode;
  preselectedReviewId?: string;
  preselectedContractId?: string;
}

/** If the URL has a typo'd UUID, pick the sole list entry with the same prefix. */
function resolveReviewIdFromList(requestedId: string, reviews: ReviewSummary[]): string | null {
  if (reviews.some((r) => r.review_id === requestedId)) return requestedId;
  const prefix = requestedId.slice(0, 15);
  const matches = reviews.filter((r) => r.review_id.slice(0, 15) === prefix);
  return matches.length === 1 ? matches[0].review_id : null;
}

export function ReviewContextProvider({ children, preselectedReviewId, preselectedContractId }: ReviewContextProviderProps) {
  const router = useRouter();
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(
    preselectedReviewId || preselectedContractId || null,
  );
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<ReviewSection>("summary");
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);
  const [showLeftPanel, setShowLeftPanel] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [selectedRedlineId, setSelectedRedlineId] = useState<string | null>(null);
  const [redlineScrollTop, setRedlineScrollTop] = useState(0);
  const [redlineStatusFilter, setRedlineStatusFilter] = useState("");

  const { data: reviews = [], isLoading: isReviewsLoading } = useReviews();
  const { data: selectedReview, isLoading: isReviewLoading, isFetched: isReviewFetched } = useReview(selectedReviewId ?? "");
  const { data: findings = [], isLoading: isFindingsLoading } = useFindings(selectedReviewId ?? "");
  const { data: policyViolations, isLoading: isPolicyLoading } = usePolicyViolations(selectedReviewId ?? "");
  const { data: missingClauses } = useMissingClauses(selectedReviewId ?? "");
  const { data: recommendations, isLoading: isRecommendationsLoading } = useRecommendations(selectedReviewId ?? "");
  const { data: workflow, isLoading: isWorkflowLoading } = useWorkflow(selectedReviewId ?? "");
  const { data: activity, isLoading: isActivityLoading } = useActivity(selectedReviewId ?? "");
  const { data: comments } = useComments(selectedReviewId ?? "");

  // contractId maps 1:1 to review_id; sync if list loads a canonical id
  useEffect(() => {
    if (!preselectedContractId || preselectedReviewId) return;
    const match = reviews.find((r) => r.review_id === preselectedContractId);
    if (match && selectedReviewId !== match.review_id) {
      setSelectedReviewId(match.review_id);
      setReviewError(null);
    }
  }, [preselectedContractId, preselectedReviewId, reviews, selectedReviewId]);

  // Correct typo'd reviewId in URL (e.g. 49b9 vs 4969) when list has a single close match
  useEffect(() => {
    if (!selectedReviewId || isReviewsLoading || reviews.length === 0) return;
    if (selectedReview || !isReviewFetched || isReviewLoading) return;

    const resolved = resolveReviewIdFromList(selectedReviewId, reviews);
    if (resolved && resolved !== selectedReviewId) {
      setSelectedReviewId(resolved);
      setReviewError(null);
      const params = new URLSearchParams();
      params.set("reviewId", resolved);
      router.replace(`/reviews/ai-workspace?${params.toString()}`);
      return;
    }

    if (!reviews.some((r) => r.review_id === selectedReviewId)) {
      setReviewError(
        `Review "${selectedReviewId}" was not found. Open a contract from the queue or fix the reviewId in the URL.`,
      );
    }
  }, [
    selectedReviewId,
    selectedReview,
    reviews,
    isReviewsLoading,
    isReviewLoading,
    isReviewFetched,
    router,
  ]);

  // Auto-select highest-priority finding when findings load for the first time
  useEffect(() => {
    if (findings.length > 0 && !selectedFindingId && !isFindingsLoading) {
      const top = findHighestPriorityFinding(findings);
      if (top) {
        setSelectedFindingId(top.finding_id);
        setExpandedFindingId(top.finding_id);
      }
    }
  }, [findings.length, isFindingsLoading]);

  // Restore redline UI when opening a review (tab switches keep context mounted)
  useEffect(() => {
    if (!selectedReviewId) {
      setSelectedRedlineId(null);
      setRedlineScrollTop(0);
      setRedlineStatusFilter("");
      return;
    }
    const saved = loadRedlineUiState(selectedReviewId);
    setSelectedRedlineId(saved.selectedRedlineId);
    setRedlineScrollTop(saved.scrollTop);
    setRedlineStatusFilter(saved.statusFilter);
  }, [selectedReviewId]);

  // Persist redline selection + scroll while reviewing
  useEffect(() => {
    if (!selectedReviewId) return;
    saveRedlineUiState(selectedReviewId, {
      selectedRedlineId,
      scrollTop: redlineScrollTop,
      statusFilter: redlineStatusFilter,
    });
  }, [selectedReviewId, selectedRedlineId, redlineScrollTop, redlineStatusFilter]);

  const selectReview = useCallback((id: string | null) => {
    setSelectedReviewId(id);
    setSelectedFindingId(null);
    setExpandedFindingId(null);
    setActiveSection("summary");
    setReviewError(null);
    if (id) {
      const saved = loadRedlineUiState(id);
      setSelectedRedlineId(saved.selectedRedlineId);
      setRedlineScrollTop(saved.scrollTop);
      setRedlineStatusFilter(saved.statusFilter);
    } else {
      setSelectedRedlineId(null);
      setRedlineScrollTop(0);
      setRedlineStatusFilter("");
    }
  }, []);

  const value = useMemo<ReviewContextValue>(() => ({
    selectedReviewId,
    selectReview,
    reviews,
    selectedReview: selectedReview ?? null,
    findings,
    policyViolations,
    missingClauses,
    recommendations,
    workflow,
    activity,
    comments,
    isReviewsLoading,
    isReviewLoading,
    isFindingsLoading,
    isPolicyLoading,
    isRecommendationsLoading,
    isWorkflowLoading,
    isActivityLoading,
    activeSection,
    setActiveSection,
    selectedFindingId,
    setSelectedFindingId,
    expandedFindingId,
    setExpandedFindingId,
    showLeftPanel,
    setShowLeftPanel,
    showRightPanel,
    setShowRightPanel,
    selectedRedlineId,
    setSelectedRedlineId,
    redlineScrollTop,
    setRedlineScrollTop,
    redlineStatusFilter,
    setRedlineStatusFilter,
    error: reviewError,
  }), [
    selectedReviewId, selectReview, reviews, selectedReview, findings,
    policyViolations, missingClauses, recommendations, workflow, activity, comments,
    isReviewsLoading, isReviewLoading, isFindingsLoading, isPolicyLoading,
    isRecommendationsLoading, isWorkflowLoading, isActivityLoading,
    activeSection, selectedFindingId, expandedFindingId,
    showLeftPanel, showRightPanel,
    selectedRedlineId, redlineScrollTop, redlineStatusFilter,
    reviewError,
  ]);

  return (
    <ReviewContext.Provider value={value}>
      {children}
    </ReviewContext.Provider>
  );
}

export function useReviewContext(): ReviewContextValue {
  const ctx = useContext(ReviewContext);
  if (!ctx) throw new Error("useReviewContext must be used within ReviewContextProvider");
  return ctx;
}

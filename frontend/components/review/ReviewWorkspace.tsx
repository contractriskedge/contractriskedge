/**
 * ReviewWorkspace — split-pane review cockpit.
 *
 * LEFT: Contract viewer (evidence browser / chunk text)
 * RIGHT: Findings, redlines, activity with tab navigation
 *
 * Features:
 * - Immutable state banner when review is finalized/approved/rejected/archived
 * - Locked UI controls in immutable states
 * - Clicking a finding highlights the relevant clause text in the viewer
 */

"use client";

import React, { useState, useCallback, useEffect } from "react";
import { ArrowLeft, RefreshCw, PanelLeft, PanelRight, FileText, BookOpen, Lock, CheckCircle, XCircle, Edit3 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import {
  useReview,
  useReviewStatus,
  useReAnalyzeReview,
  findReviewInQueryCache,
} from "@/services/hooks";
import { reviewService } from "@/services/api/reviews";
import { useAnalysisRuns, useUploadChunks } from "@/services/hooks/useUploads";
import { ContractSummary } from "./ContractSummary";
import { FindingsTable, FindingsNavigator } from "./FindingsTable";
import { RedlinesPanel } from "./RedlinesPanel";
import { RiskBreakdownPanel } from "./RiskBreakdownPanel";
import { EvidenceViewer } from "./EvidenceViewer";
import { ActivityTimeline } from "./ActivityTimeline";
import { DocumentVersionsPanel } from "./DocumentVersionsPanel";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { DetailSkeleton, CardSkeleton } from "@/components/shared/LoadingSkeleton";
import { ReviewActions } from "./ReviewActions";
import { ImmutableBanner } from "./ImmutableBanner";
import { isImmutable, getStatusLabel } from "@/lib/workflow";
import { locateRedline, findTextInChunk } from "@/lib/locateRedline";
import type { RedlineItem } from "@/services/api/client";
import { PageHeader } from "@/components/shared/PageHeader";

interface ReviewWorkspaceProps {
  reviewId: string;
  onBack?: () => void;
}

export function ReviewWorkspace({ reviewId, onBack }: ReviewWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"findings" | "redlines" | "evidence" | "activity" | "versions">("findings");
  const [showLeftPane, setShowLeftPane] = useState(true);
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);
  const [highlightText, setHighlightText] = useState<string | null>(null);
  const [highlightNeedle, setHighlightNeedle] = useState<string | null>(null);
  const [locateTick, setLocateTick] = useState(0);
  const [expandedChunkId, setExpandedChunkId] = useState<string | null>(null);
  const [locateNotice, setLocateNotice] = useState<string | null>(null);
  const [showFindingsNav, setShowFindingsNav] = useState(false);

  const queryClient = useQueryClient();
  const reviewQuery = useReview(reviewId);
  const statusQuery = useReviewStatus(reviewId);
  const reAnalyzeMutation = useReAnalyzeReview();

  const review = reviewQuery.data ?? findReviewInQueryCache(queryClient, reviewId);
  const reviewLoading =
    reviewQuery.isPending || (reviewQuery.isFetching && !reviewQuery.data);
  const reviewError = reviewQuery.error;

  const analysisRunsQuery = useAnalysisRuns(review?.upload_id);
  const status = statusQuery.data;
  const analysisRun = analysisRunsQuery.data?.runs?.[0] ?? null;
  const uploadId = review?.upload_id;

  const chunksQuery = useUploadChunks(uploadId);
  const chunks = chunksQuery.data?.chunks ?? [];

  const versionsQuery = useQuery({
    queryKey: ["reviews", reviewId, "versions"],
    queryFn: () => reviewService.listVersions(reviewId),
    enabled: Boolean(reviewId),
    staleTime: 10_000,
  });

  // Fetch actual redline count from API for accurate badge display
  const redlinesQuery = useQuery({
    queryKey: ["reviews", reviewId, "redlines", "all"],
    queryFn: () => reviewService.listRedlines(reviewId),
    enabled: Boolean(reviewId),
    staleTime: 10_000,
  });
  const actualRedlineCount = redlinesQuery.data?.redlines?.length ?? review?.redline_count ?? 0;

  // Fetch actual findings count from API
  const findingsQuery = useQuery({
    queryKey: ["reviews", reviewId, "findings", "count"],
    queryFn: () => reviewService.listFindings(reviewId, { page_size: 1 }),
    enabled: Boolean(reviewId),
    staleTime: 10_000,
  });
  const actualFindingCount = findingsQuery.data?.total ?? review?.finding_count ?? 0;
  const currentDocVersion = versionsQuery.data?.find((v) => v.status === "current")
    ?? versionsQuery.data?.slice().sort((a, b) => b.version_number - a.version_number)[0];

  // Find finalized version for display in summary
  const finalizedVersion = versionsQuery.data?.find((v) => v.status === "finalized")
    ?? versionsQuery.data?.find((v) => v.label?.toLowerCase().includes("final"))
    ?? null;

  const handleReAnalyze = async () => {
    await reAnalyzeMutation.mutateAsync({
      reviewId,
      body: { review_id: reviewId, reason: "Manual re-analysis requested" },
    });
  };

  // When a finding is selected from FindingsTable, highlight its chunk
  const handleFindingSelect = useCallback((chunkId: string | null) => {
    setSelectedChunkId(chunkId);
    if (chunkId) {
      setActiveTab("evidence");
    }
  }, []);

  // Listen for mitigation:filter-findings events from the Top Actions Widget
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail?.category) {
        setActiveTab("findings");
        // Small delay to let the tab render before scrolling
        setTimeout(() => {
          const el = document.querySelector('[data-findings-section]');
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "start" });
            el.classList.add("ring-2", "ring-emerald-400", "ring-offset-2", "rounded-lg", "transition-all", "duration-1000");
            setTimeout(() => {
              el.classList.remove("ring-2", "ring-emerald-400", "ring-offset-2", "rounded-lg");
            }, 2000);
          }
        }, 100);
      }
    };
    window.addEventListener("mitigation:filter-findings", handler);
    return () => window.removeEventListener("mitigation:filter-findings", handler);
  }, []);

  const scrollToChunk = useCallback((chunkId: string, phrase: string, needle: string) => {
    setLocateTick((t) => t + 1);
    setExpandedChunkId(chunkId);
    setSelectedChunkId(null);
    setHighlightText(null);
    setHighlightNeedle(null);

    requestAnimationFrame(() => {
      setSelectedChunkId(chunkId);
      setHighlightText(phrase);
      setHighlightNeedle(needle);
      setTimeout(() => {
        const el = document.getElementById(`chunk-${chunkId}`);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.classList.add("ring-2", "ring-yellow-400", "bg-yellow-50", "transition-all", "duration-1000");
          setTimeout(() => {
            el.classList.remove("ring-2", "ring-yellow-400", "bg-yellow-50");
          }, 3000);
        }
      }, 50);
    });
  }, []);

  // When a redline Locate is clicked, find the best matching chunk + phrase
  const handleRedlineSelect = useCallback(
    (redline: RedlineItem & { locator?: any }) => {
      if (!showLeftPane) setShowLeftPane(true);
      const located = locateRedline(redline, chunks);
      if (located) {
        setLocateNotice(located.notice ?? null);
        if (located.chunk_id && located.highlightText) {
          scrollToChunk(located.chunk_id, located.highlightText, located.needle ?? "");
        } else if (located.section_id) {
          // INSERT_NEW or UNRESOLVED with section info — show banner instead of scrolling
          setSelectedChunkId(null);
          setHighlightText(null);
          setHighlightNeedle(null);
        }
      } else {
        setSelectedChunkId(null);
        setHighlightText(null);
        setHighlightNeedle(null);
        setLocateNotice(
          "Could not find this clause in the contract text.",
        );
      }
    },
    [chunks, scrollToChunk, showLeftPane],
  );

  const tabs = [
    { id: "findings" as const, label: "Findings", count: actualFindingCount },
    { id: "redlines" as const, label: "Redlines", count: actualRedlineCount },
    { id: "evidence" as const, label: "Evidence" },
    { id: "versions" as const, label: "Versions" },
    { id: "activity" as const, label: "Activity" },
  ];

  return (
    <div className="flex h-full min-h-[calc(100vh-10rem)] flex-col">
      {/* ── Navigation Bar ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 flex-shrink-0">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              onClick={onBack}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-navy-700"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          )}
          <PageHeader
            title={review?.document_name || review?.original_filename || "Review Detail"}
            description="Analyze findings, policy violations, redlines, and approval decisions in the AI Review Workspace."
            className="!block"
          />
          {/* Toggle left pane */}
          <button
            onClick={() => setShowLeftPane(!showLeftPane)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700"
            title={showLeftPane ? "Hide contract viewer" : "Show contract viewer"}
          >
            {showLeftPane ? <PanelLeft className="w-4 h-4" /> : <PanelRight className="w-4 h-4" />}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReAnalyze}
            disabled={reAnalyzeMutation.isPending || (review ? isImmutable(review.status) : false)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-navy-600 dark:text-gray-200 dark:hover:bg-navy-700"
            title={review && isImmutable(review.status) ? `Cannot re-analyze in '${getStatusLabel(review.status)}' state` : "Re-analyze contract"}
          >
            <RefreshCw className={`h-4 w-4 ${reAnalyzeMutation.isPending ? "animate-spin" : ""}`} />
            Re-analyze
          </button>
        </div>
      </div>

      {/* ── Split Pane Content ── */}
      <div className="flex-1 flex min-h-0">
        {/* LEFT PANE: Contract Viewer / Evidence Browser */}
        {showLeftPane && (
          <div className="w-1/2 min-w-0 border-r border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 overflow-y-auto">
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <BookOpen className="w-3.5 h-3.5" />
                Contract Text
                <span className="text-gray-400 font-normal normal-case">({chunks.length} chunks)</span>
              </div>
              {locateNotice && (
                <p className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
                  {locateNotice}
                </p>
              )}
              {chunksQuery.isLoading ? (
                <CardSkeleton count={5} />
              ) : chunks.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <FileText className="w-10 h-10 text-gray-300 mb-3" />
                  <p className="text-sm text-gray-500">No contract text available</p>
                  <p className="text-xs text-gray-400 mt-1">Upload a document to view its extracted content here.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {chunks.map((chunk) => {
                    const isHighlighted = selectedChunkId === chunk.chunk_id;
                    // Sentence-level highlight: find the exact text within the chunk
                    let displayText = chunk.text;
                    let beforeHighlight = "";
                    let highlightedPhrase = "";
                    let afterHighlight = "";

                    if (isHighlighted && chunk.text) {
                      const searchNeedle = highlightNeedle || highlightText || "";
                      if (searchNeedle) {
                        const hit =
                          findTextInChunk(chunk.text, searchNeedle) ||
                          findTextInChunk(chunk.text, searchNeedle);
                        if (hit) {
                          const phrase = hit.phrase;
                          const idx = chunk.text.toLowerCase().indexOf(phrase.toLowerCase());
                          if (idx >= 0) {
                            const endIdx = Math.min(
                              idx + (highlightText?.length ?? phrase.length),
                              chunk.text.length,
                            );
                            beforeHighlight = chunk.text.slice(0, idx);
                            highlightedPhrase = chunk.text.slice(idx, endIdx);
                            afterHighlight = chunk.text.slice(endIdx);
                            displayText = "";
                          }
                        }
                      }
                    }

                    const showFullChunk =
                      expandedChunkId === chunk.chunk_id || !displayText;

                    return (
                      <div
                        key={`${chunk.chunk_id}-${isHighlighted ? locateTick : 0}`}
                        id={`chunk-${chunk.chunk_id}`}
                        className={`rounded-lg border p-3 transition-all duration-500 ${
                          isHighlighted
                            ? "border-blue-400 bg-blue-50 dark:border-blue-600 dark:bg-blue-900/20 shadow-md"
                            : "border-gray-200 hover:border-gray-300 dark:border-navy-700 dark:hover:border-gray-600"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1.5 text-[10px] text-gray-400">
                          <span>Chunk {chunk.chunk_index + 1}</span>
                          {chunk.page_numbers.length > 0 && (
                            <>
                              <span>|</span>
                              <span>Page {chunk.page_numbers.join(", ")}</span>
                            </>
                          )}
                          {chunk.section_heading && (
                            <>
                              <span>|</span>
                              <span className="font-medium text-gray-500">{chunk.section_heading}</span>
                            </>
                          )}
                          {chunk.clause_type && (
                            <span className="ml-auto rounded-full bg-gray-100 px-1.5 py-0.5 dark:bg-navy-700">
                              {chunk.clause_type.replace(/_/g, " ")}
                            </span>
                          )}
                        </div>
                        <p className="text-xs leading-relaxed text-gray-700 dark:text-gray-200">
                          {displayText ? (
                            !showFullChunk && chunk.text.length > 500
                              ? `${chunk.text.slice(0, 500)}...`
                              : chunk.text
                          ) : (
                            <>
                              {beforeHighlight}
                              <mark className="bg-yellow-200 text-yellow-900 rounded px-0.5 animate-pulse">
                                {highlightedPhrase}
                              </mark>
                              {afterHighlight}
                            </>
                          )}
                        </p>
                        {chunk.text && chunk.text.length > 500 && !showFullChunk && (
                          <button
                            onClick={() => setExpandedChunkId(chunk.chunk_id)}
                            className="mt-1 text-[10px] text-blue-600 hover:text-blue-800"
                          >
                            Show full chunk
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* RIGHT PANE: Review Detail */}
        <div className={`flex-1 min-w-0 overflow-y-auto ${showLeftPane ? "" : ""}`}>
          <div className="p-6 space-y-6">
            {/* Contract Summary */}
            <AsyncBoundary
              isLoading={reviewLoading}
              error={reviewError}
              isEmpty={!reviewLoading && !reviewError && !review}
              loadingSkeleton={<DetailSkeleton />}
              emptyMessage="Review not found"
              emptyDescription="This review could not be loaded. Try again or return to the queue."
              onRetry={() => reviewQuery.refetch()}
            >
              {review ? (
                <>
                  {/* Immutable state banner for finalized/approved/rejected/archived */}
                  <ImmutableBanner status={review.status} />

                  {/* KPI Cards — risk score, risk level, findings count, redlines count */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg border border-gray-200 bg-white shadow-sm">
                      <p className="text-xs text-gray-500 mb-0.5">Risk Score</p>
                      <p className="text-xl font-bold text-gray-900">
                        {review.risk_score != null
                          ? `${(review.risk_score * 100).toFixed(0)}%`
                          : "—"}
                      </p>
                    </div>
                    <div className="p-3 rounded-lg border border-gray-200 bg-white shadow-sm">
                      <p className="text-xs text-gray-500 mb-0.5">Risk Level</p>
                      <p className={`text-xl font-bold ${
                        review.risk_score == null ? "text-gray-400" :
                        review.risk_score >= 0.81 ? "text-red-600" :
                        review.risk_score >= 0.61 ? "text-orange-600" :
                        review.risk_score >= 0.41 ? "text-amber-600" :
                        review.risk_score >= 0.21 ? "text-yellow-600" :
                        "text-green-600"
                      }`}>
                        {review.risk_score == null ? "—" :
                          review.risk_score >= 0.81 ? "Critical" :
                          review.risk_score >= 0.61 ? "High" :
                          review.risk_score >= 0.41 ? "Elevated" :
                          review.risk_score >= 0.21 ? "Moderate" :
                          "Minimal"}
                      </p>
                    </div>
                    <div className="p-3 rounded-lg border border-gray-200 bg-white shadow-sm">
                      <p className="text-xs text-gray-500 mb-0.5">Findings</p>
                      <p className="text-xl font-bold text-gray-900">{actualFindingCount}</p>
                    </div>
                    <div className="p-3 rounded-lg border border-gray-200 bg-white shadow-sm">
                      <p className="text-xs text-gray-500 mb-0.5">Redlines</p>
                      <p className="text-xl font-bold text-gray-900">{actualRedlineCount}</p>
                    </div>
                  </div>

                  <ContractSummary
                    review={review}
                    status={status}
                    analysisRun={analysisRun}
                    documentVersionNumber={currentDocVersion?.version_number}
                    documentVersionLabel={currentDocVersion?.label ?? undefined}
                    finalizedVersion={finalizedVersion ? {
                      version_id: finalizedVersion.version_id,
                      version_number: finalizedVersion.version_number,
                      checksum_sha256: finalizedVersion.checksum_sha256,
                      storage_key: finalizedVersion.storage_key,
                    } : null}
                  />

                  {/* Risk Breakdown — explainability panel */}
                  <RiskBreakdownPanel reviewId={reviewId} />

                  {/* Review Actions Bar */}
                  <ReviewActions reviewId={reviewId} review={review} />

                  {/* Sticky Findings Navigator — priority queue */}
                  {activeTab === "findings" && review && (
                    <FindingsNavigator reviewId={reviewId} total={review.finding_count ?? 0} />
                  )}

                  {/* Tab Navigation */}
                  <div className="border-b border-gray-200 dark:border-navy-700">
                    <nav className="-mb-px flex gap-6" aria-label="Review sections">
                      {tabs.map((tab) => (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`relative whitespace-nowrap pb-3 text-sm font-medium transition-colors ${
                            activeTab === tab.id
                              ? "text-blue-600 dark:text-blue-400"
                              : "text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-300"
                          }`}
                        >
                          {tab.label}
                          {tab.count != null && (
                            <span className={`ml-1.5 rounded-full px-2 py-0.5 text-xs ${
                              activeTab === tab.id
                                ? "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                                : "bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-gray-300"
                            }`}>
                              {tab.count}
                            </span>
                          )}
                          {activeTab === tab.id && (
                            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 dark:bg-blue-400" />
                          )}
                        </button>
                      ))}
                    </nav>
                  </div>

                  {/* Tab Content */}
                  <div className="space-y-6">
                    {activeTab === "findings" && (
                      <div data-findings-section>
                        <React.Suspense fallback={<div className="text-center py-8 text-gray-400 text-sm">Loading findings...</div>}>
                          <FindingsTable reviewId={reviewId} onFindingSelect={handleFindingSelect} review={review} />
                        </React.Suspense>
                      </div>
                    )}
                    {activeTab === "redlines" && (
                      <React.Suspense fallback={<div className="text-center py-8 text-gray-400 text-sm">Loading redlines...</div>}>
                        <RedlinesPanel reviewId={reviewId} onRedlineSelect={handleRedlineSelect} review={review} />
                      </React.Suspense>
                    )}
                    {activeTab === "evidence" && uploadId && (
                      <React.Suspense fallback={<div className="text-center py-8 text-gray-400 text-sm">Loading evidence...</div>}>
                        <EvidenceViewer uploadId={uploadId} />
                      </React.Suspense>
                    )}
                    {activeTab === "activity" && (
                      <React.Suspense fallback={<div className="text-center py-8 text-gray-400 text-sm">Loading activity...</div>}>
                        <ActivityTimeline reviewId={reviewId} />
                      </React.Suspense>
                    )}
                    {activeTab === "versions" && (
                      <React.Suspense fallback={<div className="text-center py-8 text-gray-400 text-sm">Loading versions...</div>}>
                        <DocumentVersionsPanel reviewId={reviewId} />
                      </React.Suspense>
                    )}
                  </div>
                </>
              ) : null}
            </AsyncBoundary>
          </div>
        </div>
      </div>
    </div>
  );
}

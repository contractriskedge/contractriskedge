/**
 * ReviewDetailView — Example of using React Query hooks for a review detail page.
 *
 * Demonstrates:
 * - useReview() for data fetching
 * - useReviewStatus() for polling
 * - AsyncBoundary for loading/error/empty states
 * - useResolveFinding() for optimistic mutations
 * - Cache invalidation patterns
 *
 * This is a reference implementation. Integrate into your actual views.
 */

"use client";

import React, { useState } from "react";
import {
  useReview,
  useReviewStatus,
  useReviewFindings,
  useReviewRedlines,
  useReviewComments,
  useResolveFinding,
  useUpdateRedline,
  useAddComment,
} from "@/services/hooks";
import { AsyncBoundary, ErrorDisplay, EmptyState } from "@/components/shared/AsyncBoundary";
import { DetailSkeleton, TableSkeleton, CardSkeleton } from "@/components/shared/LoadingSkeleton";

interface ReviewDetailViewProps {
  reviewId: string;
}

export function ReviewDetailView({ reviewId }: ReviewDetailViewProps) {
  const [findingFilter, setFindingFilter] = useState<string>();

  // ── Queries ──
  const reviewQuery = useReview(reviewId);
  const statusQuery = useReviewStatus(reviewId);
  const findingsQuery = useReviewFindings(reviewId, { severity: findingFilter });
  const redlinesQuery = useReviewRedlines(reviewId);
  const commentsQuery = useReviewComments(reviewId);

  // ── Mutations ──
  const resolveFindingMutation = useResolveFinding(reviewId);
  const updateRedlineMutation = useUpdateRedline(reviewId);
  const addCommentMutation = useAddComment(reviewId);

  // ── Derived State ──
  const review = reviewQuery.data;
  const status = statusQuery.data;
  const progress = status?.progress ?? 0;
  const currentStep = status?.current_step;
  const isProcessing = status && status.status !== "completed" && status.status !== "failed" && progress < 100;

  // ── Render ──

  return (
    <div className="space-y-6">
      {/* Status Bar */}
      {status && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                status.status === "completed" ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                : status.status === "failed" ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                : "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
              }`}>
                {status.status}
              </span>
              {currentStep && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {currentStep}
                </span>
              )}
            </div>
            {isProcessing && (
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {progress}%
              </span>
            )}
          </div>
          {isProcessing && (
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
              <div
                className="h-full rounded-full bg-blue-500 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
          {status.error && (
            <div className="mt-3 rounded-md bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
              {status.error}
            </div>
          )}
        </div>
      )}

      {/* Review Detail */}
      <AsyncBoundary
        isLoading={reviewQuery.isLoading}
        error={reviewQuery.error}
        isEmpty={!review}
        loadingSkeleton={<DetailSkeleton />}
        emptyMessage="Review not found"
        onRetry={() => reviewQuery.refetch()}
      >
        {review && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-gray-100">
              Review {review.review_id.slice(0, 8)}...
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400">Status</span>
                <p className="font-medium text-gray-900 dark:text-gray-100">{review.status}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400">Findings</span>
                <p className="font-medium text-gray-900 dark:text-gray-100">{review.finding_count}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400">Redlines</span>
                <p className="font-medium text-gray-900 dark:text-gray-100">{review.redline_count}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400">Priority</span>
                <p className="font-medium text-gray-900 dark:text-gray-100">{review.priority}</p>
              </div>
            </div>
          </div>
        )}
      </AsyncBoundary>

      {/* Findings */}
      <div>
        <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Findings ({findingsQuery.data?.total ?? 0})
        </h3>
        <AsyncBoundary
          isLoading={findingsQuery.isLoading}
          error={findingsQuery.error}
          isEmpty={!findingsQuery.data?.findings?.length}
          loadingSkeleton={<TableSkeleton rows={4} columns={4} />}
          emptyMessage="No findings"
          emptyDescription="AI analysis has not identified any risks in this contract."
          onRetry={() => findingsQuery.refetch()}
        >
          {findingsQuery.data?.findings && (
            <div className="space-y-3">
              {findingsQuery.data.findings.map((finding) => (
                <div
                  key={finding.finding_id}
                  className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        finding.severity === "critical" || finding.severity === "high"
                          ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                          : finding.severity === "medium"
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400"
                          : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                      }`}>
                        {finding.severity}
                      </span>
                      <h4 className="mt-1 font-medium text-gray-900 dark:text-gray-100">
                        {finding.title}
                      </h4>
                    </div>
                    {finding.confidence && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {Math.round(finding.confidence * 100)}% confidence
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    {finding.description}
                  </p>
                  {finding.recommendation && (
                    <p className="mt-2 text-sm text-blue-600 dark:text-blue-400">
                      Recommendation: {finding.recommendation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  );
}

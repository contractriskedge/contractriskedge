/**
 * AsyncBoundary — declarative loading, empty, and error state handler.
 *
 * Wraps async data displays with consistent loading skeletons,
 * empty states, and error displays. Eliminates boilerplate
 * conditional rendering across all components.
 *
 * Usage:
 *   <AsyncBoundary
 *     isLoading={isLoading}
 *     error={error}
 *     isEmpty={data?.length === 0}
 *     emptyMessage="No reviews found"
 *     loadingSkeleton={<CardSkeleton count={3} />}
 *     onRetry={() => refetch()}
 *   >
 *     <ActualContent data={data} />
 *   </AsyncBoundary>
 *
 *   // With a single data item:
 *   <AsyncBoundary
 *     isLoading={isLoading}
 *     error={error}
 *     isEmpty={!data}
 *     loadingSkeleton={<DetailSkeleton />}
 *   >
 *     <ReviewDetailView review={data} />
 *   </AsyncBoundary>
 */

"use client";

import React from "react";
import { AlertTriangle, RefreshCw, Inbox, FileX } from "lucide-react";
import { CardSkeleton } from "./LoadingSkeleton";

// ── Types ─────────────────────────────────────────────────────────

interface AsyncBoundaryProps {
  /** Loading state */
  isLoading: boolean;
  /** Error object from React Query or catch block */
  error?: Error | null;
  /** Whether data is empty (null, undefined, or empty array) */
  isEmpty?: boolean;
  /** Message to show when data is empty */
  emptyMessage?: string;
  /** Detailed description for empty state */
  emptyDescription?: string;
  /** Icon to show in empty state (default: Inbox) */
  emptyIcon?: React.ReactNode;
  /** Custom loading skeleton (default: CardSkeleton) */
  loadingSkeleton?: React.ReactNode;
  /** Callback for retry button */
  onRetry?: () => void;
  /** Children to render when data is ready */
  children: React.ReactNode;
}

// ── Error Display ─────────────────────────────────────────────────

interface ErrorDisplayProps {
  error: Error;
  onRetry?: () => void;
  fullPage?: boolean;
}

export function ErrorDisplay({
  error,
  onRetry,
  fullPage = false,
}: ErrorDisplayProps) {
  const containerClass = fullPage
    ? "flex min-h-[400px] items-center justify-center"
    : "flex items-center justify-center py-12";

  return (
    <div className={containerClass}>
      <div className="mx-auto max-w-md text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Something went wrong
        </h3>
        <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
          {error.message || "An unexpected error occurred. Please try again."}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </button>
        )}
      </div>
    </div>
  );
}

// ── Empty State Display ───────────────────────────────────────────

interface EmptyStateProps {
  message?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({
  message = "No data available",
  description,
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="mb-4 text-gray-300 dark:text-gray-600">
        {icon || <Inbox className="h-12 w-12" />}
      </div>
      <h3 className="mb-1 text-lg font-medium text-gray-900 dark:text-gray-100">
        {message}
      </h3>
      {description && (
        <p className="mb-4 max-w-sm text-center text-sm text-gray-500 dark:text-gray-400">
          {description}
        </p>
      )}
      {action}
    </div>
  );
}

// ── Main AsyncBoundary ────────────────────────────────────────────

export function AsyncBoundary({
  isLoading,
  error,
  isEmpty = false,
  emptyMessage = "No data available",
  emptyDescription,
  emptyIcon,
  loadingSkeleton = <CardSkeleton count={3} />,
  onRetry,
  children,
}: AsyncBoundaryProps) {
  // Loading state
  if (isLoading) {
    return <>{loadingSkeleton}</>;
  }

  // Error state
  if (error) {
    return <ErrorDisplay error={error} onRetry={onRetry} />;
  }

  // Empty state
  if (isEmpty) {
    return (
      <EmptyState
        message={emptyMessage}
        description={emptyDescription}
        icon={emptyIcon}
      />
    );
  }

  // Data ready
  return <>{children}</>;
}

// ── Specialized Error for Not Found ───────────────────────────────

interface NotFoundProps {
  message?: string;
  description?: string;
}

export function NotFoundState({
  message = "Resource not found",
  description = "The requested resource could not be found. It may have been deleted or you may not have access.",
}: NotFoundProps) {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <div className="mx-auto max-w-md text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/30">
          <FileX className="h-6 w-6 text-amber-600 dark:text-amber-400" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
          {message}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {description}
        </p>
      </div>
    </div>
  );
}

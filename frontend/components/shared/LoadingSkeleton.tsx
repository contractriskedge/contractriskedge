/**
 * Loading skeleton components for async data states.
 *
 * Provides consistent loading placeholders across all views.
 * Supports cards, tables, text lines, and custom layouts.
 *
 * Usage:
 *   import { LoadingSkeleton, CardSkeleton, TableSkeleton, TextSkeleton } from '@/components/shared/LoadingSkeleton';
 *
 *   {isLoading && <CardSkeleton count={3} />}
 *   {isLoading && <TableSkeleton rows={5} columns={4} />}
 *   {isLoading && <LoadingSkeleton className="h-48 rounded-xl" />}
 */

"use client";

import React from "react";

// ── Base Skeleton Block ───────────────────────────────────────────

interface SkeletonProps {
  className?: string;
}

function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200 dark:bg-gray-700 ${className}`}
      aria-hidden="true"
    />
  );
}

// ── Generic Loading Skeleton (single block) ───────────────────────

interface LoadingSkeletonProps {
  className?: string;
}

export function LoadingSkeleton({ className = "" }: LoadingSkeletonProps) {
  return <Skeleton className={className} />;
}

// ── Card Skeleton ─────────────────────────────────────────────────

interface CardSkeletonProps {
  count?: number;
  columns?: 1 | 2 | 3 | 4;
}

export function CardSkeleton({ count = 1, columns = 3 }: CardSkeletonProps) {
  const gridCols = {
    1: "grid-cols-1",
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <div className={`grid ${gridCols[columns]} gap-4`} role="status">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800"
        >
          <Skeleton className="mb-3 h-4 w-3/4" />
          <Skeleton className="mb-2 h-3 w-1/2" />
          <Skeleton className="mb-2 h-3 w-5/6" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      ))}
    </div>
  );
}

// ── Table Skeleton ────────────────────────────────────────────────

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
  className = "",
}: TableSkeletonProps) {
  return (
    <div className={`overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 ${className}`} role="status">
      {/* Header */}
      <div className="border-b border-gray-200 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex gap-4">
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton key={i} className="h-4 flex-1" />
          ))}
        </div>
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={rowIdx}
          className="border-b border-gray-100 px-4 py-3 last:border-0 dark:border-gray-700"
        >
          <div className="flex gap-4">
            {Array.from({ length: columns }).map((_, colIdx) => (
              <Skeleton
                key={colIdx}
                className={`h-4 ${colIdx === 0 ? "flex-[2]" : "flex-1"}`}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Text Skeleton ─────────────────────────────────────────────────

interface TextSkeletonProps {
  lines?: number;
  className?: string;
}

export function TextSkeleton({ lines = 3, className = "" }: TextSkeletonProps) {
  return (
    <div className={`space-y-2 ${className}`} role="status">
      {Array.from({ length: lines }).map((_, i) => {
        const width = i === lines - 1 ? "w-2/3" : "w-full";
        return (
          <Skeleton
            key={i}
            className={`h-4 ${width}`}
          />
        );
      })}
    </div>
  );
}

// ── Detail Page Skeleton ──────────────────────────────────────────

export function DetailSkeleton() {
  return (
    <div className="space-y-6" role="status">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-40" />
        </div>
        <Skeleton className="h-10 w-32 rounded-lg" />
      </div>
      {/* Content grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <TextSkeleton lines={6} />
          </div>
        </div>
        <div>
          <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <TextSkeleton lines={4} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Status Badge Skeleton ─────────────────────────────────────────

export function BadgeSkeleton() {
  return <Skeleton className="inline-block h-5 w-20 rounded-full" />;
}

// ── Progress Skeleton ─────────────────────────────────────────────

export function ProgressSkeleton() {
  return (
    <div className="space-y-1" role="status">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-3 w-8" />
      </div>
      <Skeleton className="h-2 w-full rounded-full" />
    </div>
  );
}

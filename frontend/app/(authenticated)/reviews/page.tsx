/**
 * Reviews route — enterprise review queue.
 * Opens reviews in the dedicated AI Review Workspace.
 */

"use client";

import React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Brain, ArrowRight, ListChecks } from "lucide-react";
import { ReviewQueue } from "@/components/review/ReviewQueue";

export default function ReviewsPage() {
  const router = useRouter();

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-navy-900">
      {/* ── Enterprise Header ── */}
      <div className="flex items-center justify-between px-6 py-3 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 flex-shrink-0">
        <div className="flex items-center gap-3">
          <ListChecks className="w-5 h-5 text-navy-600 dark:text-navy-300" />
          <div>
            <h1 className="text-base font-bold text-navy-900 dark:text-white">Review Queue</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">Manage and process contract reviews across the enterprise</p>
          </div>
        </div>
        <Link
          href="/reviews/ai-workspace"
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-600 text-white hover:bg-navy-700 transition-colors"
        >
          <Brain className="w-3.5 h-3.5" />
          AI Review Workspace
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      {/* ── Full-Width Queue ── */}
      <div className="flex-1 overflow-y-auto">
        <ReviewQueue onReviewSelect={(reviewId) => router.push(`/reviews/ai-workspace?reviewId=${reviewId}`)} />
      </div>
    </div>
  );
}

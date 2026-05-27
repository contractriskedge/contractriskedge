/**
 * ClauseIntelligenceView — Clause relationship graph and knowledge base.
 *
 * Sprint 7 Priority 3.
 *
 * Provides:
 * - Clause relationship graph visualization (force-directed graph)
 * - Alternative and fallback clause browser
 * - Vendor clause profile view
 * - Negotiation history timeline
 * - Clause co-occurrence analysis
 *
 * Status: Scaffold — pending Sprint 7 implementation.
 */

"use client";

import React from "react";

interface ClauseIntelligenceViewProps {
  reviewId?: string;
  vendorId?: string;
}

export function ClauseIntelligenceView({ reviewId, vendorId }: ClauseIntelligenceViewProps) {
  return (
    <div className="p-6">
      <div className="bg-gradient-to-br from-teal-50 to-emerald-50 dark:from-teal-900/20 dark:to-emerald-900/20 rounded-xl border border-teal-200 dark:border-teal-800 p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-teal-100 dark:bg-teal-800 flex items-center justify-center">
          <svg className="w-8 h-8 text-teal-600 dark:text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-navy-900 dark:text-white mb-2">Clause Intelligence</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
          Explore clause relationships, approved alternatives, fallback language, and
          negotiation patterns. Build a proprietary knowledge layer from your contract history.
        </p>
        <div className="flex items-center justify-center gap-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700 dark:bg-teal-800 dark:text-teal-300">
            Sprint 7
          </span>
          <span className="text-xs text-gray-400">|</span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-800 dark:text-yellow-300">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
            In Development
          </span>
        </div>
      </div>
    </div>
  );
}

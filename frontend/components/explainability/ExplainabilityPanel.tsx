/**
 * ExplainabilityPanel — AI evidence chains and confidence visualization.
 *
 * Sprint 7 Priority 2.
 *
 * Provides:
 * - Evidence chain tree view (expandable reasoning path per finding)
 * - Confidence score indicator with dimension breakdown
 * - Clause citation panel (exact text that triggered findings)
 * - Precedent contract linkage
 * - Regulation citation mapping
 * - Alternative recommendation cards
 *
 * Status: Scaffold — pending Sprint 7 implementation.
 */

"use client";

import React from "react";

interface ExplainabilityPanelProps {
  reviewId: string;
  findingId?: string;
}

export function ExplainabilityPanel({ reviewId, findingId }: ExplainabilityPanelProps) {
  return (
    <div className="p-6">
      <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl border border-purple-200 dark:border-purple-800 p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-purple-100 dark:bg-purple-800 flex items-center justify-center">
          <svg className="w-8 h-8 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-navy-900 dark:text-white mb-2">AI Explainability</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
          Understand why the AI reached each conclusion. View evidence chains, clause citations,
          precedent references, confidence scores, and alternative recommendations.
        </p>
        <div className="flex items-center justify-center gap-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-800 dark:text-purple-300">
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

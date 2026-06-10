"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import type { SearchResult } from "./types";

// ── DISABLED ─────────────────────────────────────────────────────
// Quick Preview Drawer was previously rendering 100% mock data across
// all tabs (overview, insights, clauses, relationships, workflow,
// obligations, activity, similar). This is dangerous because users
// would think they're viewing live contract data.
//
// Re-enable only when a real backend endpoint exists that returns
// QuickPreviewData for a given search result.
//
// See: SearchAudit.md — Critical #2
// ─────────────────────────────────────────────────────────────────

interface QuickPreviewDrawerProps {
  result: SearchResult | null;
  isOpen: boolean;
  onClose: () => void;
}

export function QuickPreviewDrawer({ isOpen }: QuickPreviewDrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-2xl p-8 max-w-md text-center">
        <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-6 h-6 text-amber-500" />
        </div>
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-2">Quick Preview Unavailable</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
          This feature is temporarily disabled because it was displaying simulated data.
          A real backend endpoint is required before re-enabling.
        </p>
      </div>
    </div>
  );
}

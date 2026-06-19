/**
 * RedlineActions — Action buttons for redline cards with permission enforcement.
 *
 * Shows Accept, Reject, Edit, and Regenerate buttons based on:
 * 1. Redline status (only shown for "proposed" redlines)
 * 2. User permissions (hides buttons when user lacks workflows:write)
 * 3. Finding-to-redline mapping validity
 *
 * Backend enforcement: PUT /reviews/{id}/redlines/{id} requires WORKFLOWS_WRITE.
 */

"use client";

import React from "react";
import {
  CheckCircle2, XCircle, Edit3, RefreshCw,
} from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import type { RedlineItem } from "@/services/api/client";

interface RedlineActionsProps {
  redline: RedlineItem;
  findingCategoryMismatch: boolean;
  onAccept?: (redlineId: string) => void;
  onReject?: (redlineId: string) => void;
  onEdit?: (redline: RedlineItem) => void;
  onRegenerate?: (redline: RedlineItem) => void;
}

export function RedlineActions({
  redline,
  findingCategoryMismatch,
  onAccept,
  onReject,
  onEdit,
  onRegenerate,
}: RedlineActionsProps) {
  const { hasPermission } = useAuth();

  // Check if user has permission to modify redlines
  // Backend requires WORKFLOWS_WRITE — match that here
  const canModify = hasPermission("workflows:write") || hasPermission("*");

  if (!canModify) {
    return (
      <div className="mt-3 flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-800">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          You have read-only access. Redline actions are not available.
        </span>
      </div>
    );
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700">
      {/* Accept is hidden when finding-to-redline mapping is invalid */}
      {!findingCategoryMismatch && onAccept && (
        <button
          onClick={() => onAccept(redline.redline_id)}
          className="inline-flex items-center gap-1.5 rounded-md bg-green-100 px-3 py-1.5 text-xs font-medium text-green-700 transition-colors hover:bg-green-200 dark:bg-green-900/30 dark:text-green-300 dark:hover:bg-green-800"
        >
          <CheckCircle2 className="h-3.5 w-3.5" /> Accept
        </button>
      )}
      {/* Reject is hidden when mapping is invalid — use Regenerate instead */}
      {!findingCategoryMismatch && onReject && (
        <button
          onClick={() => onReject(redline.redline_id)}
          className="inline-flex items-center gap-1.5 rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-200 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-800"
        >
          <XCircle className="h-3.5 w-3.5" /> Reject
        </button>
      )}
      {!findingCategoryMismatch && onEdit && (
        <button
          onClick={() => onEdit(redline)}
          className="inline-flex items-center gap-1.5 rounded-md bg-purple-100 px-3 py-1.5 text-xs font-medium text-purple-700 transition-colors hover:bg-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:hover:bg-purple-800"
        >
          <Edit3 className="h-3.5 w-3.5" /> Edit
        </button>
      )}
      {/* Regenerate button for invalid mappings — uses finding.category as mandatory filter */}
      {findingCategoryMismatch && onRegenerate && (
        <button
          onClick={() => onRegenerate(redline)}
          className="inline-flex items-center gap-1.5 rounded-md bg-amber-100 px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:hover:bg-amber-800"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Regenerate Redline
        </button>
      )}
    </div>
  );
}

/**
 * Operation-aware redline body (insert vs replace/modification).
 *
 * For INSERT operations: strips AI-hallucinated section numbers from proposed_text.
 * Uses legal redline diff (word-level spans) — not whole-paragraph green highlighting.
 */

"use client";

import React from "react";
import type { RedlineItem } from "@/services/api/client";
import { InlineDiffViewer } from "./InlineDiffViewer";

const LEADING_SECTION_RE = /^(?:§\s*)?(?:\d+(?:\.\d+)*|[IVXLCDM]+)[.\s)\t]+/i;

function stripSectionNumbers(text: string): string {
  if (!text) return text;
  return text
    .split("\n")
    .map((line) => {
      const trimmed = line.trim();
      if (trimmed && LEADING_SECTION_RE.test(trimmed)) {
        return trimmed.replace(LEADING_SECTION_RE, "").trim();
      }
      return line;
    })
    .join("\n");
}

const OPERATION_LABELS: Record<string, string> = {
  insert: "New clause",
  modification: "Modification",
  replace: "Replacement",
  delete: "Deletion",
};

const OPERATION_COLORS: Record<string, string> = {
  insert: "bg-emerald-100 text-emerald-800",
  modification: "bg-blue-100 text-blue-700",
  replace: "bg-purple-100 text-purple-700",
  delete: "bg-red-100 text-red-700",
};

export function RedlineContent({ redline }: { redline: RedlineItem }) {
  const op = redline.operation || "modification";
  const isInsert = op === "insert";
  const isModified = redline.status === "modified" || Boolean(redline.reviewer_modified_text);
  const opLabel = isModified && isInsert ? "Modified clause" : OPERATION_LABELS[op] || op;
  const opColor = isModified
    ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
    : OPERATION_COLORS[op] || OPERATION_COLORS.modification;

  const displayProposed = isInsert
    ? stripSectionNumbers(redline.proposed_text)
    : redline.proposed_text;
  const displayAi = isInsert && redline.ai_proposed_text
    ? stripSectionNumbers(redline.ai_proposed_text)
    : redline.ai_proposed_text;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${opColor}`}>
          {opLabel}
        </span>
        {isInsert && !isModified && (
          <span className="text-[10px] text-gray-500 dark:text-gray-400">
            Adds new language — does not replace the contract header or unrelated sections
          </span>
        )}
        {isModified && (
          <span className="text-[10px] text-purple-600 dark:text-purple-400">
            Customized from AI suggestion
          </span>
        )}
      </div>

      {isInsert && redline.anchor_text && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Insert after: <span className="font-medium text-gray-700 dark:text-gray-300">&ldquo;{redline.anchor_text}&rdquo;</span>
        </p>
      )}

      <InlineDiffViewer
        original={isInsert ? "" : redline.original_text}
        proposed={displayProposed}
        aiProposedText={displayAi}
        reviewerModifiedText={redline.reviewer_modified_text}
        isModified={isModified}
        reviewedBy={redline.reviewed_by}
        mode="inline"
        existingContext={isInsert ? redline.context_excerpt ?? undefined : undefined}
      />

      {isInsert && redline.context_excerpt && redline.anchor_text && (
        <details className="rounded-lg border border-gray-200 bg-gray-50/80 px-3 py-2 text-xs dark:border-gray-700 dark:bg-gray-800/50">
          <summary className="cursor-pointer font-medium text-gray-500 dark:text-gray-400">
            Surrounding text at insertion point
          </summary>
          <p className="mt-2 text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
            {redline.context_excerpt}
          </p>
        </details>
      )}
    </div>
  );
}

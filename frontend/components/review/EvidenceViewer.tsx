/**
 * Evidence Viewer — explainability layer showing source text for AI findings.
 *
 * Shows: chunk text, source page, clause evidence, similarity score.
 * This is the trust layer — enterprise users need to see WHY the AI made a finding.
 */

"use client";

import React, { useState } from "react";
import { FileText, BookOpen, ExternalLink, Search, ChevronDown, ChevronUp } from "lucide-react";
import { useUploadChunks } from "@/services/hooks/useUploads";
import type { UploadChunkResponse } from "@/services/api/uploads";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";

interface EvidenceViewerProps {
  uploadId: string;
  findingChunkIds?: string[];
  className?: string;
}

export function EvidenceViewer({ uploadId, findingChunkIds, className = "" }: EvidenceViewerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);

  const chunksQuery = useUploadChunks(uploadId);
  const allChunks = chunksQuery.data?.chunks ?? [];

  // Filter chunks: by finding IDs or search query
  const chunks = findingChunkIds && findingChunkIds.length > 0
    ? allChunks.filter((c) => findingChunkIds.includes(c.chunk_id))
    : searchQuery
      ? allChunks.filter((c) =>
          c.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (c.clause_type && c.clause_type.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (c.section_heading && c.section_heading.toLowerCase().includes(searchQuery.toLowerCase()))
        )
      : allChunks.slice(0, 20); // Show first 20 by default

  return (
    <div className={`rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800 ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-100 px-5 py-4 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Evidence Viewer
            </h2>
            {findingChunkIds && (
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                {findingChunkIds.length} chunks
              </span>
            )}
          </div>
          {/* Search */}
          {!findingChunkIds && (
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search evidence..."
                className="w-48 rounded-lg border border-gray-300 py-1.5 pl-8 pr-3 text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
              />
            </div>
          )}
        </div>
      </div>

      {/* Body */}
      <AsyncBoundary
        isLoading={chunksQuery.isLoading}
        error={chunksQuery.error}
        isEmpty={chunks.length === 0}
        loadingSkeleton={<CardSkeleton count={3} />}
        emptyMessage="No evidence available"
        emptyDescription={searchQuery ? "No chunks match your search." : "No chunks found for this document."}
        onRetry={() => chunksQuery.refetch()}
      >
        <div className="divide-y divide-gray-100 dark:divide-gray-700">
          {chunks.map((chunk) => {
            const isExpanded = expandedChunk === chunk.chunk_id;
            const truncated = chunk.text.length > 300;

            return (
              <div key={chunk.chunk_id} className="px-5 py-3">
                {/* Chunk metadata */}
                <div className="mb-2 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <FileText className="h-3.5 w-3.5" />
                  <span>Chunk {chunk.chunk_index + 1}</span>
                  {chunk.page_numbers.length > 0 && (
                    <>
                      <span className="text-gray-300 dark:text-gray-600">|</span>
                      <span>Page {chunk.page_numbers.join(", ")}</span>
                    </>
                  )}
                  {chunk.section_heading && (
                    <>
                      <span className="text-gray-300 dark:text-gray-600">|</span>
                      <span className="font-medium">{chunk.section_heading}</span>
                    </>
                  )}
                  {chunk.clause_type && (
                    <>
                      <span className="text-gray-300 dark:text-gray-600">|</span>
                      <span className="rounded-full bg-gray-100 px-1.5 py-0.5 dark:bg-gray-700">
                        {chunk.clause_type.replace(/_/g, " ")}
                      </span>
                    </>
                  )}
                  <span className="ml-auto">{chunk.token_count} tokens</span>
                </div>

                {/* Chunk text */}
                <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                  {isExpanded || !truncated ? chunk.text : `${chunk.text.slice(0, 300)}...`}
                </p>

                {/* Expand/collapse */}
                {truncated && (
                  <button
                    onClick={() => setExpandedChunk(isExpanded ? null : chunk.chunk_id)}
                    className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    {isExpanded ? (
                      <>Show less <ChevronUp className="h-3 w-3" /></>
                    ) : (
                      <>Show more <ChevronDown className="h-3 w-3" /></>
                    )}
                  </button>
                )}

                {/* Similarity score (if available) */}
                {chunk.similarity_score != null && (
                  <div className="mt-2 flex items-center gap-1.5">
                    <div className="h-1.5 flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
                      <div
                        className="h-full rounded-full bg-blue-500"
                        style={{ width: `${chunk.similarity_score * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 dark:text-gray-500">
                      {Math.round(chunk.similarity_score * 100)}% match
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </AsyncBoundary>

      {/* Chunk count */}
      {allChunks.length > 0 && (
        <div className="border-t border-gray-100 px-5 py-2 text-center text-xs text-gray-400 dark:border-gray-700 dark:text-gray-500">
          {allChunks.length} total chunks
          {findingChunkIds && findingChunkIds.length > 0
            ? ` • ${findingChunkIds.length} relevant to selected finding`
            : null}
        </div>
      )}
    </div>
  );
}

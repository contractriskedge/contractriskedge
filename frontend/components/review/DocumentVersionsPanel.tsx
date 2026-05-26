/**
 * DocumentVersionsPanel — immutable version history for contract documents.
 *
 * Shows:
 * - Version timeline with labels (v1 Original, v2 AI Redlines, etc.)
 * - Download buttons for each version
 * - Status badges (current, archived, draft, finalized)
 * - Change summary per version
 * - SHA-256 checksum for finalized versions
 * - Immutable badge for finalized versions
 */

"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Download, FileText, Clock, Loader2, CheckCircle, Archive, GitCompare, Lock, Fingerprint, ShieldCheck } from "lucide-react";
import { reviewService } from "@/services/api/reviews";
import { VersionDiffViewer } from "./VersionDiffViewer";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface DocumentVersion {
  version_id: string;
  review_id: string;
  version_number: number;
  label: string | null;
  status: string;
  source_document_id: string | null;
  storage_key: string | null;
  change_summary: string | null;
  accepted_redline_ids: string[];
  file_size_bytes: number | null;
  mime_type: string | null;
  checksum_sha256: string | null;
  created_by: string;
  created_at: string;
}

interface DocumentVersionsPanelProps {
  reviewId: string;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / 1048576).toFixed(1)}MB`;
}

const VERSION_LABELS: Record<number, string> = {
  1: "Original Upload",
  2: "AI Redlines Applied",
  3: "Legal Review Updates",
  4: "Final Approved Copy",
};

const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  current: { bg: "bg-green-100", text: "text-green-700", icon: <CheckCircle className="w-3 h-3" /> },
  archived: { bg: "bg-gray-100", text: "text-gray-600", icon: <Archive className="w-3 h-3" /> },
  draft: { bg: "bg-amber-100", text: "text-amber-700", icon: <Clock className="w-3 h-3" /> },
  approved_redlines: { bg: "bg-green-100", text: "text-green-700", icon: <CheckCircle className="w-3 h-3" /> },
  finalized: { bg: "bg-emerald-100", text: "text-emerald-700", icon: <Lock className="w-3 h-3" /> },
};

export function DocumentVersionsPanel({ reviewId }: DocumentVersionsPanelProps) {
  const [showDiff, setShowDiff] = useState(false);
  const { data: versions, isLoading } = useQuery<DocumentVersion[]>({
    queryKey: ["reviews", reviewId, "versions"],
    queryFn: () => reviewService.listVersions(reviewId),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
      </div>
    );
  }

  const items = versions ?? [];

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center py-12 text-center">
        <FileText className="w-10 h-10 text-gray-300 mb-3" />
        <p className="text-sm text-gray-500">No document versions yet</p>
        <p className="text-xs text-gray-400 mt-1">Versions are created when redlines are accepted.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Compare button */}
      {items.length >= 2 && (
        <button
          onClick={() => setShowDiff(!showDiff)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-900 text-white hover:bg-navy-800 transition-colors mb-2"
        >
          <GitCompare className="w-3.5 h-3.5" />
          {showDiff ? "Hide Diff Viewer" : "Compare Versions"}
        </button>
      )}

      {/* Diff Viewer */}
      <AnimatePresence>
        {showDiff && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <VersionDiffViewer reviewId={reviewId} />
          </motion.div>
        )}
      </AnimatePresence>

      {items.map((version, idx) => {
        const cfg = STATUS_CONFIG[version.status] || STATUS_CONFIG.draft;
        const label = version.label || VERSION_LABELS[version.version_number] || `v${version.version_number}`;
        return (
          <motion.div
            key={version.version_id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="flex items-start gap-4 p-4 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
          >
            {/* Version number badge */}
            <div className="w-10 h-10 rounded-lg bg-navy-900 flex items-center justify-center flex-shrink-0">
              <span className="text-sm font-bold text-white">v{version.version_number}</span>
            </div>

            {/* Version details */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="text-sm font-semibold text-navy-900">{label}</h4>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-medium ${cfg.bg} ${cfg.text}`}>
                  {cfg.icon}
                  {version.status}
                </span>
              </div>

              {version.change_summary && (
                <p className="text-xs text-gray-500 mt-1">{version.change_summary}</p>
              )}

              <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
                <span>{formatDate(version.created_at)}</span>
                <span>by {version.created_by}</span>
                {version.file_size_bytes && <span>{formatFileSize(version.file_size_bytes)}</span>}
                {version.accepted_redline_ids.length > 0 && (
                  <span>{version.accepted_redline_ids.length} redlines applied</span>
                )}
                {version.status === "finalized" && (
                  <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                    <ShieldCheck className="w-3 h-3" />
                    Immutable
                  </span>
                )}
              </div>
              {/* SHA-256 checksum for finalized versions */}
              {version.status === "finalized" && (version as any).checksum_sha256 && (
                <div className="mt-1 flex items-center gap-1.5 text-[9px] text-gray-400 dark:text-gray-500 font-mono">
                  <Fingerprint className="w-2.5 h-2.5" />
                  SHA-256: {(version as any).checksum_sha256.substring(0, 20)}...
                </div>
              )}
            </div>

            <div className="flex flex-col items-end gap-1 flex-shrink-0">
              {version.storage_key ? (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => {
                      window.open(
                        `${API_BASE}/reviews/${reviewId}/versions/${version.version_id}/export-tracked`,
                        "_blank",
                      );
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-purple-100 text-purple-700 hover:bg-purple-200 transition-colors"
                    title="Download with tracked changes markup"
                  >
                    <FileText className="w-3 h-3" />
                    Tracked
                  </button>
                  <button
                    onClick={() => {
                      window.open(
                        `${API_BASE}/reviews/${reviewId}/versions/${version.version_id}/download`,
                        "_blank",
                      );
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors"
                  >
                    <Download className="w-3 h-3" />
                    Download
                  </button>
                </div>
              ) : version.version_number >= 2 && version.accepted_redline_ids.length > 0 ? (
                <span className="text-[10px] text-amber-600 max-w-[120px] text-right">
                  Generating file… refresh this tab
                </span>
              ) : null}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

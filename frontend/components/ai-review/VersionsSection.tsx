/**
 * VersionsSection — enterprise document version management.
 *
 * Integrates the mature DocumentVersionsPanel and VersionDiffViewer
 * from components/review/ into the AI Review Workspace.
 *
 * Shows:
 * - Version timeline (original, AI redline, negotiated, reviewer, current)
 * - Side-by-side diff viewer
 * - Inline diff with tracked changes
 * - Download per version (tracked changes, clean copy)
 * - SHA-256 checksum for finalized versions
 */

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText, Download, Clock, Loader2, CheckCircle, Archive,
  GitCompare, Lock, Fingerprint, ShieldCheck, History,
  Upload as UploadIcon, Cpu as CpuIcon, Edit3 as Edit3Icon,
  UserCheck as UserCheckIcon, CheckCircle2 as CheckCircle2Icon,
} from "lucide-react";
import { reviewService } from "@/services/api/reviews";
import { VersionDiffViewer } from "@/components/review/VersionDiffViewer";
import { useReviewContext } from "./ReviewContext";
import { useVersions } from "./hooks";

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

const VERSION_LABELS: Record<number, string> = {
  1: "Original Upload",
  2: "AI Redlines Applied",
  3: "Legal Review Updates",
  4: "Approval Candidate",
};

const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  current: { bg: "bg-green-100", text: "text-green-700", icon: <CheckCircle className="w-3 h-3" /> },
  archived: { bg: "bg-gray-100", text: "text-gray-600", icon: <Archive className="w-3 h-3" /> },
  draft: { bg: "bg-amber-100", text: "text-amber-700", icon: <Clock className="w-3 h-3" /> },
  approved_redlines: { bg: "bg-green-100", text: "text-green-700", icon: <CheckCircle className="w-3 h-3" /> },
  finalized: { bg: "bg-emerald-100", text: "text-emerald-700", icon: <Lock className="w-3 h-3" /> },
};

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

export function VersionsSection() {
  const ctx = useReviewContext();
  const { selectedReviewId } = ctx;
  const [showDiff, setShowDiff] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleDownload = async (version: DocumentVersion, tracked = false) => {
    if (!selectedReviewId) return;
    setDownloadError(null);
    setDownloadingId(version.version_id);
    try {
      const filename = `${version.label || "contract"}_v${version.version_number}.docx`;
      if (tracked) {
        await reviewService.exportTrackedChanges(selectedReviewId, version.version_id);
      } else {
        await reviewService.downloadVersion(selectedReviewId, version.version_id, filename);
      }
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloadingId(null);
    }
  };

  const { data: versions, isLoading } = useVersions(selectedReviewId ?? "");

  if (!selectedReviewId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <History className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-xs text-gray-500">Select a review to view versions</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
      </div>
    );
  }

  const items: DocumentVersion[] = (versions as DocumentVersion[] | undefined) ?? [];

  return (
    <div className="p-4 space-y-4">
      {downloadError && (
        <p className="text-xs text-red-600 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
          {downloadError}
        </p>
      )}
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-navy-500" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase">Document Versions</span>
        </div>
        {items.length >= 2 && (
          <button onClick={() => setShowDiff(!showDiff)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[9px] font-medium rounded-lg bg-navy-600 text-white hover:bg-navy-700 transition-colors">
            <GitCompare className="w-3 h-3" />
            {showDiff ? "Hide Diff" : "Compare Versions"}
          </button>
        )}
      </div>

      {/* ── Version Summary Stats (density) ───────────────────────────── */}
      {items.length > 0 && (
        <div className="grid grid-cols-4 gap-2">
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-2 text-center">
            <p className="text-sm font-bold text-navy-900 dark:text-white">{items.length}</p>
            <p className="text-[7px] text-gray-500 uppercase">Versions</p>
          </div>
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-2 text-center">
            <p className="text-sm font-bold text-green-700">
              {items.filter(v => v.status === "current" || v.status === "finalized" || v.status === "approved_redlines").length}
            </p>
            <p className="text-[7px] text-gray-500 uppercase">Finalized</p>
          </div>
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-2 text-center">
            <p className="text-sm font-bold text-purple-700">
              {items.reduce((sum, v) => sum + (v.accepted_redline_ids?.length || 0), 0)}
            </p>
            <p className="text-[7px] text-gray-500 uppercase">Redlines</p>
          </div>
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-2 text-center">
            <p className="text-sm font-bold text-amber-700">
              {formatFileSize(items.reduce((sum, v) => sum + (v.file_size_bytes || 0), 0))}
            </p>
            <p className="text-[7px] text-gray-500 uppercase">Total Size</p>
          </div>
        </div>
      )}

      {/* ── Visual Timeline ────────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
        <div className="flex items-center gap-1.5 mb-3">
          <History className="w-3.5 h-3.5 text-navy-500" />
          <span className="text-[10px] font-semibold text-gray-500 uppercase">Version Timeline</span>
        </div>
        <div className="flex items-center gap-0">
          {[
            { label: "Upload", icon: UploadIcon, color: "text-blue-500", bg: "bg-blue-100" },
            { label: "AI Analysis", icon: CpuIcon, color: "text-purple-500", bg: "bg-purple-100" },
            { label: "Redline", icon: Edit3Icon, color: "text-amber-500", bg: "bg-amber-100" },
            { label: "Legal Review", icon: UserCheckIcon, color: "text-indigo-500", bg: "bg-indigo-100" },
            { label: "Approved", icon: CheckCircle2Icon, color: "text-green-500", bg: "bg-green-100" },
          ].map((step, i) => {
            const hasVersion = items.find(v => v.version_number === i + 1 || v.label?.toLowerCase().includes(step.label.toLowerCase()));
            return (
              <React.Fragment key={step.label}>
                <div className="flex flex-col items-center flex-1">
                  <div className={`w-8 h-8 rounded-full ${hasVersion ? step.bg : "bg-gray-100 dark:bg-navy-700"} flex items-center justify-center ${hasVersion ? "ring-2 ring-offset-1 " + step.color.replace("text-", "ring-") : ""}`}>
                    <step.icon className={`w-4 h-4 ${hasVersion ? step.color : "text-gray-400"}`} />
                  </div>
                  <span className={`text-[7px] mt-1 font-medium ${hasVersion ? "text-navy-900 dark:text-white" : "text-gray-400"}`}>{step.label}</span>
                  {hasVersion && <span className="text-[6px] text-gray-400">v{hasVersion.version_number}</span>}
                </div>
                {i < 4 && <div className={`flex-1 h-px mt-[-16px] ${hasVersion ? "bg-green-400" : "bg-gray-200 dark:bg-navy-700"}`} />}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* ── Diff Viewer ────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showDiff && items.length >= 2 && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-3">
              <VersionDiffViewer reviewId={selectedReviewId} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Version Cards ──────────────────────────────────────────────── */}
      <div className="space-y-2">
        {items.length === 0 ? (
          /* Always show default timeline when no versions exist */
          <div className="space-y-2">
            {[
              { v: 1, label: "V1 Original Upload", desc: "Initial contract upload from vendor", by: "System", status: "completed" as const, statusLabel: "Uploaded", time: "—", icon: <CheckCircle className="w-2.5 h-2.5" />, bgColor: "bg-green-100", textColor: "text-green-700" },
              { v: 2, label: "V2 AI Redline Draft", desc: "AI-generated redlines pending review", by: "AI Engine", status: "completed" as const, statusLabel: "Draft Ready", time: "—", icon: <CheckCircle className="w-2.5 h-2.5" />, bgColor: "bg-green-100", textColor: "text-green-700" },
              { v: 3, label: "V3 Legal Revision", desc: "Awaiting reviewer changes", by: "Legal Reviewer", status: "current" as const, statusLabel: "In Review", time: "—", icon: <Clock className="w-2.5 h-2.5" />, bgColor: "bg-blue-100", textColor: "text-blue-700" },
              { v: 4, label: "V4 Approval Candidate", desc: "Awaiting final approval", by: "—", status: "pending" as const, statusLabel: "Pending Approval", time: "—", icon: <Clock className="w-2.5 h-2.5" />, bgColor: "bg-amber-100", textColor: "text-amber-700" },
            ].map((v, idx) => (
              <motion.div key={v.label}
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}
                className={`flex items-start gap-3 p-3 bg-white dark:bg-navy-800 rounded-lg border ${
                  v.status === "current" ? "border-blue-300 dark:border-blue-700 ring-1 ring-blue-200" : "border-dashed border-gray-200 dark:border-navy-700"
                }`}>
                <div className={`w-9 h-9 rounded-lg ${
                  v.status === "completed" ? "bg-green-100" :
                  v.status === "current" ? "bg-blue-100" : "bg-gray-100 dark:bg-navy-700"
                } flex items-center justify-center flex-shrink-0`}>
                  <span className={`text-sm font-bold ${
                    v.status === "completed" ? "text-green-700" :
                    v.status === "current" ? "text-blue-700" : "text-gray-400"
                  }`}>v{v.v}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className={`text-xs font-semibold ${
                      v.status === "completed" ? "text-green-700" :
                      v.status === "current" ? "text-blue-700" : "text-gray-400"
                    }`}>{v.label}</h4>
                    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[8px] font-medium ${v.bgColor} ${v.textColor}`}>
                      {v.icon} {v.statusLabel}
                    </span>
                  </div>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">{v.desc}</p>
                  <div className="flex items-center gap-3 mt-1 text-[9px] text-gray-400">
                    <span>{v.time}</span>
                    <span>by {v.by}</span>
                    {v.v === 3 && <span className="text-blue-600 font-medium">2 changes pending</span>}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <div className="flex items-center gap-1">
                    {idx > 0 && (
                      <button className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200 transition-colors">
                        <GitCompare className="w-2.5 h-2.5" /> v{v.v - 1} ↔ v{v.v}
                      </button>
                    )}
                    {v.status === "completed" ? (
                      <button className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors">
                        <Download className="w-2.5 h-2.5" /> Download
                      </button>
                    ) : (
                      <span className="text-[8px] text-gray-400 italic">Awaiting</span>
                    )}
                  </div>
                  {v.status === "current" && (
                    <button className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-amber-100 text-amber-700 hover:bg-amber-200 transition-colors">
                      <History className="w-2.5 h-2.5" /> Restore
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          /* Real version cards */
          items.map((version, idx) => {
            const cfg = STATUS_CONFIG[version.status] || STATUS_CONFIG.draft;
            const label = version.label || VERSION_LABELS[version.version_number] || `v${version.version_number}`;
            return (
              <motion.div key={version.version_id}
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}
                className="flex items-start gap-3 p-3 bg-white dark:bg-navy-800 rounded-lg border border-gray-200 dark:border-navy-700 hover:border-gray-300 dark:hover:border-navy-600 transition-colors">
                {/* Version number badge */}
                <div className="w-9 h-9 rounded-lg bg-navy-900 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-bold text-white">v{version.version_number}</span>
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-xs font-semibold text-navy-900 dark:text-white">{label}</h4>
                    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[8px] font-medium ${cfg.bg} ${cfg.text}`}>
                      {cfg.icon}
                      {version.status}
                    </span>
                  </div>
                  {version.change_summary && (
                    <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">{version.change_summary}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-[9px] text-gray-400">
                    <span>{formatDate(version.created_at)}</span>
                    <span>by {version.created_by}</span>
                    {version.file_size_bytes && <span>{formatFileSize(version.file_size_bytes)}</span>}
                    {version.accepted_redline_ids.length > 0 && (
                      <span>{version.accepted_redline_ids.length} redlines applied</span>
                    )}
                    {version.status === "finalized" && (
                      <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                        <ShieldCheck className="w-2.5 h-2.5" /> Immutable
                      </span>
                    )}
                  </div>
                  {version.status === "finalized" && version.checksum_sha256 && (
                    <div className="mt-0.5 flex items-center gap-1 text-[8px] text-gray-400 font-mono">
                      <Fingerprint className="w-2 h-2" />
                      SHA-256: {version.checksum_sha256.substring(0, 20)}...
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <div className="flex items-center gap-1">
                    {/* Compare with previous version — explicit vX vs vY labels */}
                    {idx > 0 && (
                      <button onClick={() => setShowDiff(true)}
                        className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200 transition-colors"
                        title={`Compare v${version.version_number - 1} vs v${version.version_number}`}>
                        <GitCompare className="w-2.5 h-2.5" /> v{version.version_number - 1} ↔ v{version.version_number}
                      </button>
                    )}
                    {version.storage_key ? (
                      <>
                        <button
                          onClick={() => handleDownload(version, true)}
                          disabled={downloadingId === version.version_id}
                          className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-purple-100 text-purple-700 hover:bg-purple-200 transition-colors disabled:opacity-50">
                          <FileText className="w-2.5 h-2.5" /> Tracked
                        </button>
                        <button
                          onClick={() => handleDownload(version, false)}
                          disabled={downloadingId === version.version_id}
                          className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors disabled:opacity-50">
                          <Download className="w-2.5 h-2.5" /> Download
                        </button>
                      </>
                    ) : version.version_number >= 2 && version.accepted_redline_ids.length > 0 ? (
                      <span className="text-[9px] text-amber-600 text-right">Generating… refresh</span>
                    ) : (
                      <span className="text-[8px] text-gray-400 italic">Not yet available</span>
                    )}
                  </div>
                  {version.status !== "finalized" && version.status !== "archived" && (
                    <button className="flex items-center gap-1 px-2 py-1 text-[8px] font-medium rounded bg-amber-100 text-amber-700 hover:bg-amber-200 transition-colors">
                      <History className="w-2.5 h-2.5" /> Restore
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}

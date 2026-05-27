"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, FileText, CheckCircle, XCircle, AlertTriangle, Clock,
  Loader2, ChevronDown, ChevronRight, Eye, RefreshCw, Download,
  Trash2, Search, Filter, ArrowUpDown, HardDrive, Cloud, Share2,
  Mail, Server, Box, Brain, ScanEye, Tags, Link, FileSearch,
  MoreHorizontal, Play, Pause, FolderUp,
} from "lucide-react";
import type { ImportJob, PipelineStage, ProcessingStage } from "./types";

// ── Pipeline Visualizer ──────────────────────────────────────────────────

const stageIcons: Record<ProcessingStage, React.ReactNode> = {
  uploading: <Upload className="w-3 h-3" />,
  queued: <Clock className="w-3 h-3" />,
  ocr: <ScanEye className="w-3 h-3" />,
  classifying: <Brain className="w-3 h-3" />,
  extracting: <Tags className="w-3 h-3" />,
  validating: <CheckCircle className="w-3 h-3" />,
  relationships: <Link className="w-3 h-3" />,
  review: <FileSearch className="w-3 h-3" />,
  completed: <CheckCircle className="w-3 h-3" />,
  failed: <XCircle className="w-3 h-3" />,
};

function PipelineVisualizer({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="flex items-center gap-1">
      {stages.map((stage, i) => {
        const color = stage.status === "completed" ? "bg-green-500" :
          stage.status === "active" ? "bg-blue-500 animate-pulse" :
          stage.status === "failed" ? "bg-red-500" :
          stage.status === "skipped" ? "bg-gray-300" : "bg-gray-200 dark:bg-navy-600";
        const iconColor = stage.status === "completed" ? "text-green-500" :
          stage.status === "active" ? "text-blue-500" :
          stage.status === "failed" ? "text-red-500" : "text-gray-300";
        return (
          <div key={stage.id} className="flex items-center gap-0.5 group relative">
            <div className={`w-5 h-5 rounded-full flex items-center justify-center ${color} ${
              stage.status === "active" ? "ring-2 ring-blue-300" : ""
            }`}>
              <span className="text-white [&>svg]:w-2.5 [&>svg]:h-2.5">
                {stage.status === "active" ? <Loader2 className="animate-spin" /> : stageIcons[stage.id]}
              </span>
            </div>
            {i < stages.length - 1 && (
              <div className={`w-2 h-0.5 ${stage.status === "completed" ? "bg-green-500" : "bg-gray-200 dark:bg-navy-600"}`} />
            )}
            {/* Tooltip */}
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-navy-900 text-white text-[8px] px-1.5 py-0.5 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
              {stage.label}: {stage.status}
              {stage.confidence && ` (${stage.confidence}%)`}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return "—";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function isStuckOnTextExtraction(job: ImportJob): boolean {
  if (job.status !== "running") return false;
  const extraction = job.pipeline.find((s) => s.id === "ocr");
  return extraction?.status === "active";
}

// ── Import Job Card ──────────────────────────────────────────────────────

function ImportJobCard({ job, onPreview, onRetry }: { job: ImportJob; onPreview: () => void; onRetry?: () => void }) {
  const showResume = (job.status === "failed" || isStuckOnTextExtraction(job)) && onRetry;
  const statusColor = job.status === "completed" ? "border-green-200 bg-green-50/30 dark:border-green-900/30 dark:bg-green-900/10" :
    job.status === "failed" ? "border-red-200 bg-red-50/30 dark:border-red-900/30 dark:bg-red-900/10" :
    job.status === "running" ? "border-blue-200 bg-blue-50/30 dark:border-blue-900/30 dark:bg-blue-900/10" :
    "border-gray-200 dark:border-navy-600";
  const statusIcon = job.status === "completed" ? <CheckCircle className="w-3 h-3 text-green-500" /> :
    job.status === "failed" ? <XCircle className="w-3 h-3 text-red-500" /> :
    job.status === "running" ? <Loader2 className="w-3 h-3 text-blue-500 animate-spin" /> :
    <Clock className="w-3 h-3 text-gray-400" />;

  return (
    <motion.div layout className={`border rounded-lg overflow-hidden ${statusColor}`}>
      <div className="px-3 py-2">
        <div className="flex items-start gap-2.5">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
            job.status === "completed" ? "bg-green-100 text-green-600" :
            job.status === "failed" ? "bg-red-100 text-red-600" :
            job.status === "running" ? "bg-blue-100 text-blue-600" :
            "bg-gray-100 text-gray-400"
          }`}>
            <FileText className="w-3.5 h-3.5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold text-navy-900 dark:text-white truncate">{job.fileName}</span>
              {statusIcon}
              {job.isDuplicate && <span className="text-[8px] bg-amber-100 text-amber-700 px-1 py-0.5 rounded font-medium">Duplicate</span>}
              {job.priority === "high" && <span className="text-[8px] bg-red-100 text-red-600 px-1 py-0.5 rounded font-medium">High</span>}
            </div>
            <div className="flex items-center gap-2 text-[9px] text-gray-500 mt-0.5">
              <span className="capitalize">{job.sourceLabel}</span>
              <span>·</span>
              <span className="capitalize">{job.documentType}</span>
              <span>·</span>
              <span>{formatFileSize(job.fileSize)}</span>
              <span>·</span>
              <span>{job.submittedBy}</span>
            </div>
            {/* Pipeline */}
            <div className="mt-1.5">
              <PipelineVisualizer stages={job.pipeline} />
            </div>
            {/* Confidence Scores */}
            {job.status === "completed" && (
              <div className="flex items-center gap-2 mt-1 text-[8px] text-gray-400">
                <span>OCR: <strong className="text-green-600">{job.ocrAccuracy}%</strong></span>
                <span>Classification: <strong className="text-blue-600">{job.classificationScore}%</strong></span>
                <span>Extraction: <strong className="text-purple-600">{job.extractionScore}%</strong></span>
              </div>
            )}
            {/* Error */}
            {job.status === "failed" && job.error && (
              <div className="mt-1 flex items-start gap-1 text-[9px] text-red-600 bg-red-50 dark:bg-red-900/20 rounded p-1">
                <AlertTriangle className="w-2.5 h-2.5 mt-0.5 flex-shrink-0" />
                <span>{job.error}</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-0.5 flex-shrink-0">
            <button onClick={onPreview} className="p-1 text-gray-400 hover:text-gold-600 hover:bg-gold-50 dark:hover:bg-gold-900/20 rounded transition-colors">
              <Eye className="w-3 h-3" />
            </button>
            {showResume && (
              <button
                onClick={onRetry}
                title={job.status === "failed" ? "Retry" : "Resume extraction"}
                className="p-1 text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            )}
            <button className="p-1 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 rounded transition-colors">
              <MoreHorizontal className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── Upload Zone ──────────────────────────────────────────────────────────

function UploadZone({ onUpload }: { onUpload: (files: FileList | null) => void }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpload(e.target.files);
    // Reset so the same file can be re-selected
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    onUpload(e.dataTransfer.files);
  };

  return (
    <div
      onDragOver={e => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={handleClick}
      className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
        isDragOver
          ? "border-gold-400 bg-gold-50 dark:bg-gold-900/10 scale-[1.02]"
          : "border-gray-300 dark:border-navy-500 hover:border-gold-300 dark:hover:border-gold-600 hover:bg-gray-50 dark:hover:bg-navy-800/50"
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc,.tiff,.tif,.png,.jpg,.jpeg"
        onChange={handleFileChange}
        className="hidden"
      />
      <Upload className={`w-8 h-8 mx-auto mb-2 ${isDragOver ? "text-gold-500" : "text-gray-300 dark:text-navy-500"}`} />
      <p className="text-xs font-medium text-navy-900 dark:text-white">Drop files here or click to upload</p>
      <p className="text-[9px] text-gray-500 mt-0.5">Supports PDF, DOCX, DOC, TIFF, PNG, JPG up to 100MB</p>
      <div className="flex items-center justify-center gap-3 mt-2 text-[8px] text-gray-400">
        <span>🔒 AES-256 encrypted</span>
        <span>✓ Virus scanned</span>
        <span>📄 OCR supported</span>
      </div>
    </div>
  );
}

// ── Center Panel ─────────────────────────────────────────────────────────

interface IngestionCenterPanelProps {
  jobs: ImportJob[];
  onPreview: (job: ImportJob) => void;
  onRetry: (jobId: string) => void;
  onUpload: (files: FileList | null) => void;
}

type CenterTab = "upload" | "recent" | "all";

export function IngestionCenterPanel({ jobs, onPreview, onRetry, onUpload }: IngestionCenterPanelProps) {
  const [activeTab, setActiveTab] = useState<CenterTab>("recent");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredJobs = jobs.filter(j => {
    if (statusFilter !== "all" && j.status !== statusFilter) return false;
    if (searchQuery && !j.fileName.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const tabs: { id: CenterTab; label: string }[] = [
    { id: "upload", label: "Upload" },
    { id: "recent", label: "Recent Jobs" },
    { id: "all", label: "All Imports" },
  ];

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-navy-900">
      {/* Sub Tabs */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center gap-1">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors ${
                activeTab === tab.id ? "bg-gold-100 text-gold-700 dark:bg-gold-900/20 dark:text-gold-400" : "text-gray-500 hover:text-navy-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-navy-700"
              }`}>
              {tab.label}
            </button>
          ))}
        </div>
        {activeTab !== "upload" && (
          <div className="flex items-center gap-1.5">
            <div className="relative">
              <Search className="absolute left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
              <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search imports..."
                className="w-36 pl-6 pr-2 py-1 text-[10px] border border-gray-200 dark:border-navy-600 rounded-md bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
              />
            </div>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="text-[10px] border border-gray-200 dark:border-navy-600 rounded-md bg-transparent text-gray-500 py-1 px-1.5 focus:outline-none focus:ring-1 focus:ring-gold-400">
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="running">Running</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {activeTab === "upload" && (
          <div className="space-y-3">
            <UploadZone onUpload={onUpload} />
            {/* Batch Upload Button */}
            <button
              onClick={() => window.dispatchEvent(new CustomEvent('open-batch-upload'))}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-blue-300 dark:border-blue-600 rounded-xl text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50/50 dark:bg-blue-900/10 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
            >
              <FolderUp className="w-5 h-5" />
              Batch Upload — Multiple Files
            </button>
            {/* Quick Source Buttons */}
            <div className="grid grid-cols-3 gap-1.5">
              {[
                { icon: <HardDrive className="w-3.5 h-3.5" />, label: "Local Files" },
                { icon: <Cloud className="w-3.5 h-3.5" />, label: "Google Drive" },
                { icon: <Share2 className="w-3.5 h-3.5" />, label: "SharePoint" },
                { icon: <Mail className="w-3.5 h-3.5" />, label: "Email" },
                { icon: <Server className="w-3.5 h-3.5" />, label: "SFTP" },
                { icon: <Box className="w-3.5 h-3.5" />, label: "Box" },
              ].map(src => (
                <button key={src.label} className="flex items-center gap-1.5 px-2 py-2 border border-gray-200 dark:border-navy-600 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors text-[9px] text-gray-600 dark:text-gray-300">
                  {src.icon}
                  {src.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === "recent" && (
          <>
            {filteredJobs.slice(0, 5).map(job => (
              <ImportJobCard key={job.id} job={job} onPreview={() => onPreview(job)} onRetry={() => onRetry(job.id)} />
            ))}
          </>
        )}

        {activeTab === "all" && (
          <>
            {filteredJobs.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <FileText className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p className="text-xs">No import jobs found</p>
              </div>
            ) : (
              filteredJobs.map(job => (
                <ImportJobCard key={job.id} job={job} onPreview={() => onPreview(job)} onRetry={() => onRetry(job.id)} />
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}

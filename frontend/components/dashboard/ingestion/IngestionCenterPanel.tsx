"use client";

import React, { useState, useMemo, useCallback, useRef } from "react";
import {
  Upload, FileText, CheckCircle, XCircle, AlertTriangle, Clock,
  Loader2, Eye, RefreshCw, ChevronDown, ChevronRight, MoreHorizontal,
  HardDrive, Cloud, Share2, Mail, Server, Box,
  ArrowUpDown, Columns, Download, AlertCircle, Info,
} from "lucide-react";
import type { ImportJob, PipelineStage, ProcessingStage, TableSort, BatchAction } from "./types";

// ── Helpers ──────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const sourceIcons: Record<string, React.ReactNode> = {
  local: <HardDrive className="w-2.5 h-2.5" />,
  sharepoint: <Share2 className="w-2.5 h-2.5" />,
  googledrive: <Cloud className="w-2.5 h-2.5" />,
  box: <Box className="w-2.5 h-2.5" />,
  email: <Mail className="w-2.5 h-2.5" />,
  sftp: <Server className="w-2.5 h-2.5" />,
};

const stageLabels: Record<ProcessingStage, string> = {
  uploading: "Upload", queued: "Queue", ocr: "OCR", classifying: "AI Classify",
  extracting: "Extract", validating: "Validate", relationships: "Relationships",
  review: "Review", completed: "Done", failed: "Failed",
};

// ── Semantic Badge ───────────────────────────────────────────────────────

const statusBadge: Record<string, string> = {
  completed: "text-green-700 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-900/20 dark:border-green-800/30",
  running: "text-blue-700 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-900/20 dark:border-blue-800/30",
  failed: "text-red-700 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800/30",
  pending: "text-gray-600 bg-gray-50 border-gray-200 dark:text-gray-400 dark:bg-gray-900/20 dark:border-gray-700",
  paused: "text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-900/20 dark:border-amber-800/30",
};

function Badge({ status }: { status: string }) {
  const s = statusBadge[status] || statusBadge.pending;
  return (
    <span className={`inline-flex items-center gap-0.5 px-1 py-0.5 rounded text-[9px] font-medium border ${s}`}>
      {status === "completed" && <CheckCircle className="w-2 h-2" />}
      {status === "running" && <Loader2 className="w-2 h-2 animate-spin" />}
      {status === "failed" && <XCircle className="w-2 h-2" />}
      {status === "pending" && <Clock className="w-2 h-2" />}
      {status === "paused" && <AlertTriangle className="w-2 h-2" />}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const styles: Record<string, string> = {
    high: "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/20",
    medium: "text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20",
    low: "text-gray-500 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20",
  };
  return <span className={`text-[8px] font-medium px-1 py-0.5 rounded ${styles[priority] || styles.medium}`}>{priority}</span>;
}

// ── Mini Progress ────────────────────────────────────────────────────────

function MiniBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="w-full h-1 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
    </div>
  );
}

function StageMini({ stages }: { stages: PipelineStage[] }) {
  const active = stages.find(s => s.status === "active");
  const failed = stages.find(s => s.status === "failed");
  const done = stages.filter(s => s.status === "completed").length;
  const pct = Math.round((done / stages.length) * 100);
  if (failed) return <div className="flex items-center gap-1"><span className="text-[9px] text-red-600 font-medium">Failed</span><MiniBar pct={pct} color="bg-red-400" /></div>;
  if (active) return <div className="flex items-center gap-1"><span className="text-[9px] text-blue-600 font-medium">{active.label}</span><Loader2 className="w-2 h-2 animate-spin text-blue-500" /><MiniBar pct={active.progress} color="bg-blue-400" /></div>;
  if (pct === 100) return <div className="flex items-center gap-1"><CheckCircle className="w-2 h-2 text-green-500" /><span className="text-[9px] text-green-600 font-medium">Done</span></div>;
  return <div className="flex items-center gap-1"><Clock className="w-2 h-2 text-gray-400" /><span className="text-[9px] text-gray-400">Queued</span></div>;
}

// ── SLA Indicator ────────────────────────────────────────────────────────

function SlaIndicator({ createdAt }: { createdAt: string }) {
  const ageMs = Date.now() - new Date(createdAt).getTime();
  const ageHrs = ageMs / 3600000;
  const color = ageHrs > 24 ? "text-red-500" : ageHrs > 12 ? "text-amber-500" : "text-gray-400";
  return <span className={`text-[9px] tabular-nums ${color}`}>{ageHrs < 1 ? `${Math.round(ageMs / 60000)}m` : `${ageHrs.toFixed(1)}h`}</span>;
}

// ── Column Chooser ───────────────────────────────────────────────────────

const ALL_COLUMNS = [
  { key: "fileName", label: "Contract Name", default: true },
  { key: "source", label: "Source", default: true },
  { key: "createdAt", label: "Upload Time", default: true },
  { key: "status", label: "Status", default: true },
  { key: "confidence", label: "AI %", default: true },
  { key: "riskScore", label: "Risk", default: true },
  { key: "stage", label: "Stage", default: true },
  { key: "queue", label: "Queue", default: true },
  { key: "sla", label: "SLA", default: true },
];

// ── Sort Header ──────────────────────────────────────────────────────────

function SortHeader({ label, column, sort, onSort }: {
  label: string; column: string; sort: TableSort; onSort: (col: string) => void;
}) {
  const active = sort.column === column;
  return (
    <button onClick={() => onSort(column)} className="flex items-center gap-0.5 text-[9px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-navy-700 dark:hover:text-gray-200 transition-colors whitespace-nowrap">
      {label}
      <ArrowUpDown className={`w-2 h-2 ${active ? 'text-blue-500' : 'opacity-30'}`} />
    </button>
  );
}

// ── Contextual Actions Menu ──────────────────────────────────────────────

function ContextMenu({ job, onDetail, onRetry, onReprioritize, onAssignQueue, onRemove }: {
  job: ImportJob;
  onDetail: () => void;
  onRetry?: () => void;
  onReprioritize?: (jobId: string, priority: "high" | "medium" | "low") => void;
  onAssignQueue?: (jobId: string, queue: string) => void;
  onRemove?: (jobId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [showPrioritySub, setShowPrioritySub] = useState(false);
  const [showQueueSub, setShowQueueSub] = useState(false);
  return (
    <div className="relative">
      <button onClick={(e) => { e.stopPropagation(); setOpen(!open); setShowPrioritySub(false); setShowQueueSub(false); }} className="p-0.5 text-gray-300 hover:text-navy-600 dark:hover:text-gray-300 rounded transition-colors">
        <MoreHorizontal className="w-3 h-3" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-0.5 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded shadow-lg z-20 py-0.5 w-36">
            <button onClick={() => { onDetail(); setOpen(false); }} className="w-full text-left px-2 py-1 text-[10px] text-navy-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700">View Details</button>
            {(job.status === "failed" || job.status === "running") && onRetry && (
              <button onClick={() => { onRetry(); setOpen(false); }} className="w-full text-left px-2 py-1 text-[10px] text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20">
                {job.status === "failed" ? "Retry" : "Resume"}
              </button>
            )}
            {/* Re-prioritize with sub-menu */}
            <div className="relative">
              <button onClick={() => setShowPrioritySub(!showPrioritySub)} className="w-full text-left px-2 py-1 text-[10px] text-gray-500 hover:bg-gray-50 dark:hover:bg-navy-700 flex items-center justify-between">
                Re-prioritize <ChevronRight className="w-2 h-2" />
              </button>
              {showPrioritySub && (
                <div className="absolute left-full top-0 ml-0.5 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded shadow-lg z-30 py-0.5 w-28">
                  {(["high", "medium", "low"] as const).map(p => (
                    <button key={p} onClick={() => { onReprioritize?.(job.id, p); setOpen(false); }}
                      className="w-full text-left px-2 py-1 text-[10px] capitalize text-navy-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700">
                      {p} Priority
                    </button>
                  ))}
                </div>
              )}
            </div>
            {/* Assign Queue with sub-menu */}
            <div className="relative">
              <button onClick={() => setShowQueueSub(!showQueueSub)} className="w-full text-left px-2 py-1 text-[10px] text-gray-500 hover:bg-gray-50 dark:hover:bg-navy-700 flex items-center justify-between">
                Assign Queue <ChevronRight className="w-2 h-2" />
              </button>
              {showQueueSub && (
                <div className="absolute left-full top-0 ml-0.5 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded shadow-lg z-30 py-0.5 w-28">
                  {["priority", "standard", "bulk"].map(q => (
                    <button key={q} onClick={() => { onAssignQueue?.(job.id, q); setOpen(false); }}
                      className="w-full text-left px-2 py-1 text-[10px] capitalize text-navy-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700">
                      {q} Queue
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="border-t border-gray-100 dark:border-navy-700 my-0.5" />
            <button onClick={() => { if (confirm(`Remove "${job.fileName}"? This cannot be undone.`)) { onRemove?.(job.id); } setOpen(false); }} className="w-full text-left px-2 py-1 text-[10px] text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20">Remove</button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Detail Drawer ────────────────────────────────────────────────────────

function DetailDrawer({ job, onClose, onRetry }: { job: ImportJob; onClose: () => void; onRetry?: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="fixed inset-0 bg-black/30" onClick={onClose} />
      <div className="relative w-[420px] bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 shadow-2xl overflow-y-auto">
        <div className="sticky top-0 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 px-3 py-2 flex items-center justify-between z-10">
          <div className="flex items-center gap-1.5 min-w-0">
            <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            <h3 className="text-xs font-semibold text-navy-900 dark:text-white truncate">{job.fileName}</h3>
          </div>
          <div className="flex items-center gap-1">
            {job.status === "failed" && onRetry && (
              <button onClick={onRetry} className="flex items-center gap-1 px-1.5 py-0.5 bg-red-500 hover:bg-red-600 text-white rounded text-[9px] font-medium transition-colors"><RefreshCw className="w-2.5 h-2.5" /> Retry</button>
            )}
            <button onClick={onClose} className="p-0.5 text-gray-400 hover:text-navy-600 rounded hover:bg-gray-100 dark:hover:bg-navy-700"><XCircle className="w-3.5 h-3.5" /></button>
          </div>
        </div>
        <div className="p-3 space-y-3">
          <div className="flex items-center gap-1.5"><Badge status={job.status} /><PriorityBadge priority={job.priority} />{job.isDuplicate && <span className="text-[9px] bg-amber-100 text-amber-700 px-1 py-0.5 rounded font-medium">Duplicate</span>}</div>
          <div className="grid grid-cols-2 gap-2">
            {[{ label: "Source", value: job.sourceLabel }, { label: "Type", value: job.documentType }, { label: "Size", value: formatFileSize(job.fileSize) }, { label: "By", value: job.submittedBy }, { label: "Created", value: formatDate(job.createdAt) }, { label: "Completed", value: job.completedAt ? formatDate(job.completedAt) : "—" }].map(f => (
              <div key={f.label}><span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">{f.label}</span><p className="text-[11px] text-navy-900 dark:text-white mt-0.5">{f.value}</p></div>
            ))}
          </div>
          <div>
            <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">AI Extraction Scores</h4>
            <div className="space-y-1">
              {[{ label: "OCR", value: job.ocrAccuracy, c: "bg-blue-400" }, { label: "Classification", value: job.classificationScore, c: "bg-purple-400" }, { label: "Extraction", value: job.extractionScore, c: "bg-green-400" }, { label: "Overall", value: job.confidence, c: "bg-blue-500" }].map(s => (
                <div key={s.label} className="flex items-center gap-2"><span className="text-[9px] text-gray-500 w-16">{s.label}</span><div className="flex-1 h-1.5 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden"><div className={`h-full rounded-full ${s.c}`} style={{ width: `${s.value ?? 0}%` }} /></div><span className="text-[9px] text-gray-500 tabular-nums w-6 text-right font-medium">{s.value != null ? `${s.value}%` : "—"}</span></div>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Pipeline</h4>
            <div className="space-y-0.5">
              {job.pipeline.map(s => {
                const dot = s.status === "completed" ? "bg-green-400" : s.status === "active" ? "bg-blue-400" : s.status === "failed" ? "bg-red-400" : "bg-gray-300 dark:bg-navy-600";
                return (
                  <div key={s.id} className="flex items-center gap-1.5 text-[10px]">
                    <div className={`w-1.5 h-1.5 rounded-full ${dot}`} />
                    <span className="text-navy-700 dark:text-gray-200 w-20">{stageLabels[s.id]}</span>
                    <MiniBar pct={s.progress} color={s.status === "completed" ? "bg-green-400" : s.status === "active" ? "bg-blue-400" : s.status === "failed" ? "bg-red-400" : "bg-gray-300 dark:bg-navy-600"} />
                    <span className="text-gray-400 tabular-nums w-6 text-right">{s.progress}%</span>
                  </div>
                );
              })}
            </div>
          </div>
          {job.error && (
            <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800/30 rounded p-1.5">
              <div className="flex items-start gap-1"><AlertCircle className="w-3 h-3 text-red-500 mt-0.5" /><div><p className="text-[9px] font-semibold text-red-700 dark:text-red-400">Error</p><p className="text-[9px] text-red-600 dark:text-red-300 mt-0.5">{job.error}</p></div></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Empty State ──────────────────────────────────────────────────────────

function EmptyState({ onUpload, onOpenUploadModal }: { onUpload: (files: FileList | null) => void; onOpenUploadModal: () => void }) {
  const [isDragging, setIsDragging] = React.useState(false);

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) onUpload(e.dataTransfer.files);
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-6">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`w-full max-w-md border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
          isDragging ? "border-blue-400 bg-blue-50 dark:bg-blue-900/10" : "border-gray-200 dark:border-navy-600 hover:border-gray-300 dark:hover:border-navy-500 bg-gray-50/50 dark:bg-navy-850"
        }`}
      >
        <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragging ? "text-blue-500" : "text-gray-300"}`} />
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Drag & drop files here</p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">or</p>
        <button onClick={onOpenUploadModal} className="mt-2 text-xs font-medium px-4 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors">
          Browse Files
        </button>
        <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-2">PDF, DOCX, DOC, TIFF, PNG, JPG — up to 100MB each</p>
      </div>
      <div>
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">No contracts imported</h3>
        <p className="text-xs text-gray-500 mt-0.5 max-w-sm">Upload a contract to begin AI-powered ingestion and analysis.</p>
      </div>
    </div>
  );
}

// ── Main Center Panel ────────────────────────────────────────────────────

interface IngestionCenterPanelProps {
  jobs: ImportJob[];
  onPreview: (job: ImportJob) => void;
  onRetry: (jobId: string) => void;
  onUpload: (files: FileList | null) => void;
  onOpenUploadModal: () => void;
  onReprioritize?: (jobId: string, priority: "high" | "medium" | "low") => void;
  onAssignQueue?: (jobId: string, queue: string) => void;
  onRemove?: (jobId: string) => void;
  compactMode: boolean;
  searchQuery: string;
}

export function IngestionCenterPanel({ jobs, onPreview, onRetry, onUpload, onOpenUploadModal, onReprioritize, onAssignQueue, onRemove, compactMode, searchQuery }: IngestionCenterPanelProps) {
  const [sort, setSort] = useState<TableSort>({ column: "createdAt", direction: "desc" });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detailJob, setDetailJob] = useState<ImportJob | null>(null);
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set(ALL_COLUMNS.filter(c => c.default).map(c => c.key)));
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) onUpload(e.dataTransfer.files);
  };
  const [showColumnChooser, setShowColumnChooser] = useState(false);

  const handleSort = useCallback((col: string) => setSort(prev => ({ column: col, direction: prev.column === col && prev.direction === "asc" ? "desc" : "asc" })), []);

  const filteredJobs = useMemo(() => {
    let r = [...jobs];
    if (searchQuery) { const q = searchQuery.toLowerCase(); r = r.filter(j => j.fileName.toLowerCase().includes(q) || j.sourceLabel.toLowerCase().includes(q)); }
    r.sort((a, b) => {
      let c = 0;
      switch (sort.column) {
        case "fileName": c = a.fileName.localeCompare(b.fileName); break;
        case "source": c = a.sourceLabel.localeCompare(b.sourceLabel); break;
        case "createdAt": c = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(); break;
        case "status": c = a.status.localeCompare(b.status); break;
        case "confidence": c = (a.confidence ?? 0) - (b.confidence ?? 0); break;
        case "riskScore": c = (a.extractionScore || 0) - (b.extractionScore || 0); break;
        case "stage": { const p = { high: 0, medium: 1, low: 2 }; c = (p[a.priority] || 1) - (p[b.priority] || 1); break; }
        default: c = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      }
      return sort.direction === "asc" ? c : -c;
    });
    return r;
  }, [jobs, searchQuery, sort]);

  const toggleSelect = useCallback((id: string) => setSelectedIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; }), []);
  const toggleSelectAll = useCallback(() => setSelectedIds(prev => prev.size === filteredJobs.length ? new Set() : new Set(filteredJobs.map(j => j.id))), [filteredJobs]);

  const toggleColumn = (key: string) => setVisibleColumns(prev => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; });

  const colWidth = (key: string) => {
    if (key === "fileName") return "flex-1 min-w-[180px]";
    if (key === "source") return "w-16";
    if (key === "createdAt") return "w-20";
    if (key === "status") return "w-20";
    if (key === "confidence") return "w-20";
    if (key === "riskScore") return "w-14";
    if (key === "stage") return "w-24";
    if (key === "queue") return "w-20";
    if (key === "sla") return "w-12";
    return "flex-1";
  };

  if (filteredJobs.length === 0) return <EmptyState onUpload={onUpload} onOpenUploadModal={onOpenUploadModal} />;

  return (
    <div
      className="flex-1 flex flex-col min-w-0 bg-white dark:bg-navy-900 relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag-and-drop overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-blue-600/10 dark:bg-blue-500/10 backdrop-blur-sm rounded-lg">
          <div className="bg-white dark:bg-navy-800 border-2 border-dashed border-blue-400 rounded-xl p-8 text-center shadow-xl">
            <Upload className="w-10 h-10 mx-auto mb-3 text-blue-500" />
            <p className="text-sm font-semibold text-navy-900 dark:text-white">Drop files to upload</p>
            <p className="text-xs text-gray-500 mt-1">PDF, DOCX, DOC, TIFF, PNG, JPG</p>
          </div>
        </div>
      )}

      {/* Hidden file input for browse fallback */}
      <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.doc,.tiff,.tif,.png,.jpg,.jpeg" onChange={(e) => { if (e.target.files) onUpload(e.target.files); e.target.value = ""; }} className="hidden" />

      {/* Batch Action Bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/10 border-b border-blue-200 dark:border-blue-900/30">
          <span className="text-[10px] font-medium text-blue-700 dark:text-blue-400">{selectedIds.size} selected</span>
          <div className="w-px h-3 bg-blue-200 dark:bg-blue-800" />
          {(["retry", "reprioritize", "export", "delete"] as BatchAction[]).map(a => (
            <button key={a} onClick={() => {
              if (a === "delete") {
                if (confirm(`Remove ${selectedIds.size} selected upload(s)? This cannot be undone.`)) {
                  selectedIds.forEach(id => onRemove?.(id));
                  setSelectedIds(new Set());
                }
              } else if (a === "reprioritize") {
                const p = prompt("Set priority (high/medium/low):", "medium");
                if (p && ["high", "medium", "low"].includes(p)) {
                  selectedIds.forEach(id => onReprioritize?.(id, p as "high" | "medium" | "low"));
                  setSelectedIds(new Set());
                }
              } else if (a === "retry") {
                selectedIds.forEach(id => onRetry(id));
                setSelectedIds(new Set());
              }
            }} className="px-1.5 py-0.5 text-[9px] font-medium text-blue-700 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/20 rounded transition-colors capitalize">{a}</button>
          ))}
          <div className="flex-1" />
          <button onClick={() => setSelectedIds(new Set())} className="px-1.5 py-0.5 text-[9px] text-gray-500 hover:text-navy-700 dark:hover:text-gray-300">Clear</button>
        </div>
      )}

      {/* Sticky Table Header */}
      <div className="sticky top-0 z-10 flex items-center gap-2 px-3 py-1 border-b border-gray-200 dark:border-navy-700 bg-gray-50 dark:bg-navy-800/50">
        <div className="sticky left-0 z-20 bg-gray-50 dark:bg-navy-800/50 w-4 flex items-center"><input type="checkbox" checked={selectedIds.size === filteredJobs.length && filteredJobs.length > 0} onChange={toggleSelectAll} className="w-2.5 h-2.5 rounded border-gray-300 text-blue-500 focus:ring-blue-400" /></div>
        {ALL_COLUMNS.filter(c => visibleColumns.has(c.key)).map(col => (
          <div key={col.key} className={colWidth(col.key)}><SortHeader label={col.label} column={col.key} sort={sort} onSort={handleSort} /></div>
        ))}
        {/* Column Chooser */}
        <div className="relative ml-auto">
          <button onClick={() => setShowColumnChooser(!showColumnChooser)} className="p-0.5 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 rounded" title="Columns">
            <Columns className="w-3 h-3" />
          </button>
          {showColumnChooser && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowColumnChooser(false)} />
              <div className="absolute right-0 top-full mt-0.5 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded shadow-lg z-20 py-0.5 w-36">
                <div className="px-2 py-1 text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Columns</div>
                {ALL_COLUMNS.map(col => (
                  <label key={col.key} className="flex items-center gap-1.5 px-2 py-0.5 text-[10px] text-navy-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700 cursor-pointer">
                    <input type="checkbox" checked={visibleColumns.has(col.key)} onChange={() => toggleColumn(col.key)} className="w-2.5 h-2.5 rounded border-gray-300 text-blue-500" />
                    {col.label}
                  </label>
                ))}
              </div>
            </>
          )}
        </div>
        <div className="w-12 text-[9px] font-semibold text-gray-500 uppercase tracking-wider">Actions</div>
      </div>

      {/* Table Body */}
      <div className="flex-1 overflow-y-auto">
        {filteredJobs.map((job) => {
          const risk = job.status === "completed" && job.extractionScore != null && job.classificationScore != null && job.ocrAccuracy != null ? Math.round((job.extractionScore + job.classificationScore + job.ocrAccuracy) / 3) : 0;
          const riskColor = risk >= 90 ? "text-green-600" : risk >= 75 ? "text-amber-600" : risk > 0 ? "text-red-600" : "text-gray-400";
          const isExpanded = expandedId === job.id;
          return (
            <div key={job.id}>
              <div className={`flex items-center gap-2 px-3 py-1.5 border-b border-gray-100 dark:border-navy-800 hover:bg-gray-50 dark:hover:bg-navy-800/50 transition-colors group ${selectedIds.has(job.id) ? 'bg-blue-50/30 dark:bg-blue-900/5' : ''}`}>
                <div className="sticky left-0 z-10 bg-white dark:bg-navy-900 w-4 flex items-center"><input type="checkbox" checked={selectedIds.has(job.id)} onChange={() => toggleSelect(job.id)} className="w-2.5 h-2.5 rounded border-gray-300 text-blue-500 focus:ring-blue-400" /></div>

                {visibleColumns.has("fileName") && (
                  <div className="sticky left-4 z-10 bg-white dark:bg-navy-900 flex-1 min-w-[180px] flex items-center gap-1.5">
                    <button onClick={() => setExpandedId(isExpanded ? null : job.id)} className="p-0.5 text-gray-300 hover:text-navy-500 flex-shrink-0">{isExpanded ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}</button>
                    <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${job.status === "completed" ? "text-green-600" : job.status === "failed" ? "text-red-600" : job.status === "running" ? "text-blue-600" : "text-gray-400"}`}>
                      <FileText className="w-3 h-3" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1">
                        {job.contractNumber && <span className="text-[9px] font-mono text-gray-400 dark:text-gray-500 flex-shrink-0">{job.contractNumber}</span>}
                        <span className="text-[11px] font-medium text-navy-900 dark:text-white truncate">{job.fileName}</span>
                        {job.isDuplicate && <span className="text-[7px] bg-amber-100 text-amber-700 px-0.5 py-0.5 rounded font-medium flex-shrink-0">D</span>}
                      </div>
                      <div className="text-[8px] text-gray-400">{formatFileSize(job.fileSize)} · <span className="capitalize">{job.documentType}</span></div>
                    </div>
                  </div>
                )}

                {visibleColumns.has("source") && <div className="w-16 flex items-center gap-0.5 text-[10px] text-gray-500 dark:text-gray-300">{sourceIcons[job.source] || <HardDrive className="w-2.5 h-2.5" />}<span className="truncate">{job.sourceLabel}</span></div>}
                {visibleColumns.has("createdAt") && <div className="w-20 text-[10px] text-gray-500 dark:text-gray-400 tabular-nums">{formatDate(job.createdAt)}</div>}
                {visibleColumns.has("status") && <div className="w-20"><Badge status={job.status} /></div>}
                {visibleColumns.has("confidence") && (
                  <div className="w-20">
                    {job.status === "completed" && job.confidence != null ? (
                      <div className="flex items-center gap-1"><div className="flex-1 h-1 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden"><div className="h-full rounded-full bg-blue-400" style={{ width: `${job.confidence}%` }} /></div><span className="text-[9px] font-semibold text-navy-700 dark:text-gray-200 tabular-nums">{job.confidence}%</span></div>
                    ) : job.status === "running" ? <span className="text-[9px] text-blue-600">Processing</span> : <span className="text-[9px] text-gray-400">—</span>}
                  </div>
                )}
                {visibleColumns.has("riskScore") && <div className="w-14">{risk > 0 ? <span className={`text-[11px] font-semibold tabular-nums ${riskColor}`}>{risk}</span> : <span className="text-[9px] text-gray-400">—</span>}</div>}
                {visibleColumns.has("stage") && <div className="w-24"><StageMini stages={job.pipeline} /></div>}
                {visibleColumns.has("queue") && <div className="w-20 text-[10px] text-gray-500 dark:text-gray-400 truncate">{job.priority === "high" ? "Priority" : "Standard"}</div>}
                {visibleColumns.has("sla") && <div className="w-12"><SlaIndicator createdAt={job.createdAt} /></div>}

                <div className="w-12 flex items-center gap-0.5">
                  <button onClick={() => setDetailJob(job)} className="p-0.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors" title="View details"><Eye className="w-2.5 h-2.5" /></button>
                  {(job.status === "failed" || job.status === "running") && (
                    <button onClick={() => onRetry(job.id)} className="p-0.5 text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors" title={job.status === "failed" ? "Retry" : "Resume"}>
                      <RefreshCw className="w-2.5 h-2.5" />
                    </button>
                  )}
                  <ContextMenu job={job} onDetail={() => setDetailJob(job)} onRetry={(job.status === "failed" || job.status === "running") ? () => onRetry(job.id) : undefined} onReprioritize={onReprioritize} onAssignQueue={onAssignQueue} onRemove={onRemove} />
                </div>
              </div>

              {/* Expandable Detail Row */}
              {isExpanded && (
                <div className="bg-gray-50 dark:bg-navy-800/30 border-b border-gray-100 dark:border-navy-800 px-3 py-1.5">
                  <div className="flex items-start gap-4 text-[10px]">
                    <div><span className="text-[8px] font-semibold text-gray-400 uppercase">By</span><p className="text-navy-700 dark:text-gray-200 mt-0.5">{job.submittedBy}</p></div>
                    <div><span className="text-[8px] font-semibold text-gray-400 uppercase">Type</span><p className="text-navy-700 dark:text-gray-200 mt-0.5 capitalize">{job.documentType}</p></div>
                    <div><span className="text-[8px] font-semibold text-gray-400 uppercase">Priority</span><p className="mt-0.5"><PriorityBadge priority={job.priority} /></p></div>
                    {job.status === "completed" && (
                      <><div><span className="text-[8px] font-semibold text-gray-400 uppercase">OCR</span><p className="text-navy-700 dark:text-gray-200 mt-0.5">{job.ocrAccuracy != null ? `${job.ocrAccuracy}%` : "—"}</p></div>
                      <div><span className="text-[8px] font-semibold text-gray-400 uppercase">Class</span><p className="text-navy-700 dark:text-gray-200 mt-0.5">{job.classificationScore != null ? `${job.classificationScore}%` : "—"}</p></div>
                      <div><span className="text-[8px] font-semibold text-gray-400 uppercase">Extract</span><p className="text-navy-700 dark:text-gray-200 mt-0.5">{job.extractionScore != null ? `${job.extractionScore}%` : "—"}</p></div></>
                    )}
                    {job.error && <div className="text-red-600"><span className="text-[8px] font-semibold uppercase">Error</span><p className="mt-0.5 text-[9px]">{job.error}</p></div>}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Detail Drawer */}
      {detailJob && <DetailDrawer job={detailJob} onClose={() => setDetailJob(null)} onRetry={() => { onRetry(detailJob.id); setDetailJob(null); }} />}
    </div>
  );
}


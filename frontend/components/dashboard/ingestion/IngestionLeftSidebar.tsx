"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Cloud, Share2, Mail, Server, Box, HardDrive,
  AlertTriangle, CheckCircle, XCircle, RefreshCw, Clock,
  ChevronRight, ChevronDown, FileText, ListOrdered, Bookmark,
  Download, Trash2, Play, Pause, MoreHorizontal,
} from "lucide-react";
import type { ImportSource, ProcessingQueue, FailedImport, ImportTemplate } from "./types";

// ── Source Item ──────────────────────────────────────────────────────────

const sourceIcons: Record<string, React.ReactNode> = {
  local: <HardDrive className="w-3.5 h-3.5" />,
  sharepoint: <Share2 className="w-3.5 h-3.5" />,
  googledrive: <Cloud className="w-3.5 h-3.5" />,
  box: <Box className="w-3.5 h-3.5" />,
  email: <Mail className="w-3.5 h-3.5" />,
  sftp: <Server className="w-3.5 h-3.5" />,
};

function SourceItem({ source }: { source: ImportSource }) {
  const statusColor = source.status === "active" ? "bg-green-500" :
    source.status === "error" ? "bg-red-500" :
    source.status === "syncing" ? "bg-amber-400 animate-pulse" : "bg-gray-400";
  return (
    <div className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors">
      <div className="text-gray-400">{sourceIcons[source.type] || <HardDrive className="w-3.5 h-3.5" />}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate">{source.name}</span>
          <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${statusColor}`} />
        </div>
        <div className="flex items-center gap-1 text-[8px] text-gray-400">
          <span>{source.documentCount.toLocaleString()} docs</span>
          <span>·</span>
          <span>{source.status}</span>
        </div>
      </div>
    </div>
  );
}

// ── Queue Item ───────────────────────────────────────────────────────────

function QueueItem({ queue, onPause, onResume }: { queue: ProcessingQueue; onPause: () => void; onResume: () => void }) {
  return (
    <div className="px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${queue.status === "active" ? "bg-green-500" : queue.status === "paused" ? "bg-amber-400" : "bg-gray-400"}`} />
          <span className="text-[10px] font-medium text-navy-900 dark:text-white">{queue.name}</span>
        </div>
        <div className="flex items-center gap-0.5">
          {queue.status === "active" ? (
            <button onClick={onPause} className="p-0.5 text-gray-400 hover:text-amber-500"><Pause className="w-2.5 h-2.5" /></button>
          ) : (
            <button onClick={onResume} className="p-0.5 text-gray-400 hover:text-green-500"><Play className="w-2.5 h-2.5" /></button>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 mt-0.5 text-[8px] text-gray-400">
        <span className="text-amber-600">{queue.pendingCount} pending</span>
        <span className="text-blue-600">{queue.processingCount} active</span>
        <span>{queue.throughput}/min</span>
      </div>
    </div>
  );
}

// ── Failed Import Item ───────────────────────────────────────────────────

function FailedImportItem({ item, onRetry }: { item: FailedImport; onRetry: () => void }) {
  return (
    <div className="px-2 py-1.5 hover:bg-red-50 dark:hover:bg-red-900/10 rounded-lg transition-colors border-l-2 border-red-400">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate flex-1">{item.fileName}</span>
        <button onClick={onRetry} className="p-0.5 text-red-500 hover:text-red-700 flex-shrink-0" title="Retry">
          <RefreshCw className="w-2.5 h-2.5" />
        </button>
      </div>
      <p className="text-[8px] text-red-600 mt-0.5 truncate">{item.error}</p>
      <div className="flex items-center gap-1 mt-0.5 text-[7px] text-gray-400">
        <span className="capitalize">{item.errorType}</span>
        <span>·</span>
        <span>retry {item.retryCount}/{item.maxRetries}</span>
      </div>
    </div>
  );
}

// ── Template Item ────────────────────────────────────────────────────────

function TemplateItem({ template }: { template: ImportTemplate }) {
  return (
    <div className="px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors">
      <div className="flex items-center gap-1.5">
        <Bookmark className="w-3 h-3 text-gold-400" />
        <span className="text-[10px] font-medium text-navy-900 dark:text-white truncate">{template.name}</span>
      </div>
      <p className="text-[8px] text-gray-400 mt-0.5 truncate">{template.description}</p>
      <div className="text-[7px] text-gray-400 mt-0.5">Used {template.usageCount} times</div>
    </div>
  );
}

// ── Left Sidebar ─────────────────────────────────────────────────────────

interface IngestionLeftSidebarProps {
  sources: ImportSource[];
  queues: ProcessingQueue[];
  failedImports: FailedImport[];
  templates: ImportTemplate[];
  onRetryFailed: (id: string) => void;
  onPauseQueue: (id: string) => void;
  onResumeQueue: (id: string) => void;
}

type LeftTab = "sources" | "queues" | "failed" | "templates";

export function IngestionLeftSidebar({
  sources, queues, failedImports, templates, onRetryFailed, onPauseQueue, onResumeQueue,
}: IngestionLeftSidebarProps) {
  const [activeTab, setActiveTab] = useState<LeftTab>("sources");

  const tabs: { id: LeftTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: "sources", label: "Sources", icon: <Upload className="w-3 h-3" />, count: sources.filter(s => s.connected).length },
    { id: "queues", label: "Queues", icon: <ListOrdered className="w-3 h-3" />, count: queues.reduce((s, q) => s + q.pendingCount + q.processingCount, 0) },
    { id: "failed", label: "Failed", icon: <AlertTriangle className="w-3 h-3" />, count: failedImports.length },
    { id: "templates", label: "Templates", icon: <Bookmark className="w-3 h-3" /> },
  ];

  return (
    <div className="w-60 flex-shrink-0 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-navy-700">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 text-[9px] font-medium transition-colors relative ${
              activeTab === tab.id ? "text-gold-600 dark:text-gold-400" : "text-gray-500 dark:text-gray-400 hover:text-navy-700"
            }`}>
            {tab.icon}<span>{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span className={`text-[8px] px-1 py-0.5 rounded-full ${activeTab === tab.id ? "bg-gold-100 text-gold-700" : "bg-gray-100 text-gray-500"}`}>{tab.count}</span>
            )}
            {activeTab === tab.id && <motion.div layoutId="ing-left-tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-500" />}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {activeTab === "sources" && (
          <>
            <div className="flex items-center justify-between px-1 py-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Connected Sources</span>
              <button className="text-[8px] text-gold-600 hover:text-gold-700">+ Add</button>
            </div>
            {sources.map(s => <SourceItem key={s.id} source={s} />)}
          </>
        )}
        {activeTab === "queues" && (
          <>
            <div className="flex items-center justify-between px-1 py-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Processing Queues</span>
            </div>
            {queues.map(q => <QueueItem key={q.id} queue={q} onPause={() => onPauseQueue(q.id)} onResume={() => onResumeQueue(q.id)} />)}
          </>
        )}
        {activeTab === "failed" && (
          <>
            <div className="flex items-center justify-between px-1 py-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Failed Imports</span>
              <button className="text-[8px] text-gold-600 hover:text-gold-700">Retry All</button>
            </div>
            {failedImports.map(f => <FailedImportItem key={f.id} item={f} onRetry={() => onRetryFailed(f.id)} />)}
          </>
        )}
        {activeTab === "templates" && (
          <>
            <div className="flex items-center justify-between px-1 py-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Import Templates</span>
              <button className="text-[8px] text-gold-600 hover:text-gold-700">+ New</button>
            </div>
            {templates.map(t => <TemplateItem key={t.id} template={t} />)}
          </>
        )}
      </div>
    </div>
  );
}

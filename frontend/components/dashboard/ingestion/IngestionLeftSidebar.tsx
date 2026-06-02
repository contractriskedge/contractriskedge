"use client";

import React, { useState } from "react";
import {
  Upload, Cloud, Share2, Mail, Server, Box, HardDrive,
  AlertTriangle, CheckCircle, RefreshCw, Clock,
  ListOrdered, Bookmark, SlidersHorizontal, Filter, Search, Save,
} from "lucide-react";
import type { ImportSource, ProcessingQueue, SavedFilter } from "./types";

// ── Source Item ──────────────────────────────────────────────────────────

const sourceIcons: Record<string, React.ReactNode> = {
  local: <HardDrive className="w-3 h-3" />,
  sharepoint: <Share2 className="w-3 h-3" />,
  googledrive: <Cloud className="w-3 h-3" />,
  box: <Box className="w-3 h-3" />,
  email: <Mail className="w-3 h-3" />,
  sftp: <Server className="w-3 h-3" />,
};

function SourceItem({ source }: { source: ImportSource }) {
  const statusDot = source.status === "active" ? "bg-green-500" :
    source.status === "error" ? "bg-red-500" :
    source.status === "syncing" ? "bg-amber-500" : "bg-gray-400";
  return (
    <div className="flex items-center gap-2 px-2 py-1 hover:bg-gray-50 dark:hover:bg-navy-700 rounded transition-colors cursor-pointer group">
      <div className="text-gray-400">{sourceIcons[source.type] || <HardDrive className="w-3 h-3" />}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium text-navy-900 dark:text-white truncate">{source.name}</span>
          <div className={`w-1 h-1 rounded-full flex-shrink-0 ${statusDot}`} />
        </div>
        <div className="text-[9px] text-gray-400">{source.documentCount.toLocaleString()} docs · {source.status}</div>
      </div>
    </div>
  );
}

// ── Queue Filter Item ────────────────────────────────────────────────────

function QueueFilterItem({ queue, selected, onToggle }: { queue: ProcessingQueue; selected: boolean; onToggle: () => void }) {
  const aging = queue.avgLatency > 5000 ? "text-red-500" : queue.avgLatency > 2000 ? "text-amber-500" : "text-gray-400";
  return (
    <button onClick={onToggle} className={`w-full flex items-center gap-2 px-2 py-1 rounded transition-colors ${selected ? 'bg-gray-100 dark:bg-navy-700' : 'hover:bg-gray-50 dark:hover:bg-navy-700'}`}>
      <div className={`w-1 h-1 rounded-full ${queue.status === "active" ? "bg-green-500" : queue.status === "paused" ? "bg-amber-500" : "bg-gray-400"}`} />
      <span className="text-[11px] text-navy-900 dark:text-white flex-1 text-left truncate">{queue.name}</span>
      <span className={`text-[9px] tabular-nums ${aging}`}>{queue.avgLatency > 1000 ? `${(queue.avgLatency / 1000).toFixed(0)}s` : `${queue.avgLatency}ms`}</span>
      <span className="text-[9px] text-gray-400 tabular-nums">{queue.pendingCount}</span>
    </button>
  );
}

// ── Saved View Item ──────────────────────────────────────────────────────

function SavedViewItem({ view, onApply, onDelete }: { view: SavedFilter; onApply: () => void; onDelete: () => void }) {
  return (
    <div className="flex items-center gap-1 px-2 py-1 hover:bg-gray-50 dark:hover:bg-navy-700 rounded group transition-colors">
      <button onClick={onApply} className="flex-1 flex items-center gap-1.5 text-left min-w-0">
        <Bookmark className="w-2.5 h-2.5 text-gold-400 flex-shrink-0" />
        <span className="text-[11px] text-navy-900 dark:text-white truncate">{view.name}</span>
      </button>
      <button onClick={onDelete} className="p-0.5 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
      </button>
    </div>
  );
}

// ── Empty State ──────────────────────────────────────────────────────────

function EmptySection({ icon, title, message }: { icon: React.ReactNode; title: string; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-6 text-center px-3">
      <div className="text-gray-300 dark:text-navy-600 mb-2">{icon}</div>
      <p className="text-[10px] text-gray-400 font-medium">{title}</p>
      <p className="text-[8px] text-gray-300 dark:text-navy-500 mt-0.5">{message}</p>
    </div>
  );
}

// ── Left Sidebar ─────────────────────────────────────────────────────────

interface IngestionLeftSidebarProps {
  sources: ImportSource[];
  queues: ProcessingQueue[];
  savedViews: SavedFilter[];
  onApplyView: (view: SavedFilter) => void;
  onDeleteView: (id: string) => void;
  onToggleQueue: (queueId: string) => void;
  onAddSource: () => void;
  onSaveCurrentView: () => void;
}

type LeftTab = "sources" | "queues" | "views";

export function IngestionLeftSidebar({
  sources, queues, savedViews, onApplyView, onDeleteView, onToggleQueue, onAddSource, onSaveCurrentView,
}: IngestionLeftSidebarProps) {
  const [activeTab, setActiveTab] = useState<LeftTab>("sources");
  const [selectedQueues, setSelectedQueues] = useState<Set<string>>(new Set(queues.filter(q => q.status === "active").map(q => q.id)));

  const handleToggleQueue = (id: string) => {
    setSelectedQueues(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
    onToggleQueue(id);
  };

  const tabs: { id: LeftTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: "sources", label: "Sources", icon: <Upload className="w-3 h-3" />, count: sources.filter(s => s.connected).length },
    { id: "queues", label: "Queues", icon: <ListOrdered className="w-3 h-3" />, count: queues.reduce((s, q) => s + q.pendingCount + q.processingCount, 0) },
    { id: "views", label: "Views", icon: <Bookmark className="w-3 h-3" />, count: savedViews.length },
  ];

  return (
    <div className="w-56 flex-shrink-0 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-navy-700">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-1.5 text-[9px] font-medium transition-colors ${
              activeTab === tab.id ? "text-blue-600 dark:text-blue-400 border-b-2 border-blue-500" : "text-gray-500 dark:text-gray-400 hover:text-navy-700 dark:hover:text-gray-300"
            }`}>
            {tab.icon}<span>{tab.label}</span>
            {tab.count !== undefined && tab.count > 0 && (
              <span className={`text-[7px] px-1 py-0.5 rounded-full font-medium ${activeTab === tab.id ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : "bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-gray-400"}`}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {activeTab === "sources" && (
          <>
            <div className="flex items-center justify-between px-1 py-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Connected</span>
              <button onClick={onAddSource} className="text-[8px] text-blue-600 hover:text-blue-700 font-medium">+ Add</button>
            </div>
            {sources.length === 0 ? (
              <EmptySection icon={<Cloud className="w-5 h-5" />} title="No sources" message="Connect a document source" />
            ) : (
              sources.map(s => <SourceItem key={s.id} source={s} />)
            )}
          </>
        )}
        {activeTab === "queues" && (
          <>
            <div className="flex items-center justify-between px-1 py-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Queue Filters</span>
              <span className="text-[8px] text-gray-400">{selectedQueues.size} active</span>
            </div>
            {queues.length === 0 ? (
              <EmptySection icon={<ListOrdered className="w-5 h-5" />} title="No queues" message="Upload to create a queue" />
            ) : (
              queues.map(q => (
                <QueueFilterItem key={q.id} queue={q} selected={selectedQueues.has(q.id)} onToggle={() => handleToggleQueue(q.id)} />
              ))
            )}
            {queues.length > 0 && (
              <div className="mt-1 px-2 pt-1 border-t border-gray-100 dark:border-navy-700">
                <div className="flex items-center justify-between text-[9px] text-gray-400 py-1">
                  <span>Total pending</span>
                  <span className="font-semibold text-navy-900 dark:text-white tabular-nums">{queues.reduce((s, q) => s + q.pendingCount, 0)}</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-gray-400 py-0.5">
                  <span>Avg latency</span>
                  <span className="font-semibold text-navy-900 dark:text-white tabular-nums">{queues.length > 0 ? `${Math.round(queues.reduce((s, q) => s + q.avgLatency, 0) / queues.length / 1000)}s` : '—'}</span>
                </div>
              </div>
            )}
          </>
        )}
        {activeTab === "views" && (
          <>
            <div className="flex items-center justify-between px-1 py-1">
              <span className="text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Saved Views</span>
              <button onClick={onSaveCurrentView} className="text-[8px] text-blue-600 hover:text-blue-700 font-medium">Save</button>
            </div>
            {savedViews.length === 0 ? (
              <EmptySection icon={<Bookmark className="w-5 h-5" />} title="No saved views" message="Save a filter as a view" />
            ) : (
              savedViews.map(v => (
                <SavedViewItem key={v.id} view={v} onApply={() => onApplyView(v)} onDelete={() => onDeleteView(v.id)} />
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}


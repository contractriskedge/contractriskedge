"use client";

import React, { useState } from "react";
import {
  Upload, Link, FolderOpen, Download, Search, Filter,
  ChevronDown, Save, RotateCcw,
} from "lucide-react";
import type { ProcessingQueue, SavedFilter } from "./types";

interface IngestionToolbarProps {
  queues: ProcessingQueue[];
  onOpenUploadModal: () => void;
  onBulkImport: () => void;
  onConnectSource: () => void;
  onRetryFailed: () => void;
  onExportLogs: () => void;
  onPauseQueue: (queueId: string) => void;
  onResumeQueue: (queueId: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  compactMode: boolean;
  onToggleCompact: () => void;
  savedFilters: SavedFilter[];
  onApplyFilter: (filter: SavedFilter) => void;
  onSaveCurrentFilter: () => void;
  onToggleActivity?: () => void;
  showActivity?: boolean;
}

export function IngestionToolbar({
  queues, onOpenUploadModal, onBulkImport, onConnectSource, onRetryFailed, onExportLogs,
  onPauseQueue, onResumeQueue, searchQuery, onSearchChange,
  compactMode, onToggleCompact, savedFilters, onApplyFilter, onSaveCurrentFilter,
  onToggleActivity, showActivity,
}: IngestionToolbarProps) {
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  return (
    <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
      <div className="flex items-center justify-between px-3 py-1">
        <div className="flex items-center gap-1">
          <button onClick={onOpenUploadModal} className="flex items-center gap-1 px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-[10px] font-semibold transition-colors">
            <Upload className="w-3 h-3" /> Upload Contracts
          </button>
          <button onClick={onConnectSource} className="flex items-center gap-1 px-2 py-1 border border-gray-300 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 rounded text-[10px] font-medium text-gray-600 dark:text-gray-300 transition-colors">
            <Link className="w-2.5 h-2.5" /> Connect Source
          </button>
          <button onClick={onBulkImport} className="flex items-center gap-1 px-2 py-1 border border-gray-300 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 rounded text-[10px] font-medium text-gray-600 dark:text-gray-300 transition-colors">
            <FolderOpen className="w-2.5 h-2.5" /> Bulk Import
          </button>
          <div className="w-px h-4 bg-gray-200 dark:bg-navy-600 mx-1" />
          <button onClick={onRetryFailed} className="flex items-center gap-1 px-2 py-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded text-[10px] font-medium transition-colors">
            <RotateCcw className="w-2.5 h-2.5" /> Retry Failed
          </button>
          <button onClick={onExportLogs} className="flex items-center gap-1 px-2 py-1 text-gray-500 hover:text-navy-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 rounded text-[10px] font-medium transition-colors">
            <Download className="w-2.5 h-2.5" /> Export
          </button>
        </div>

        <div className="flex items-center gap-1.5">
          <div className="relative">
            <Search className="absolute left-1.5 top-1/2 -translate-y-1/2 w-2.5 h-2.5 text-gray-400" />
            <input type="text" value={searchQuery} onChange={e => onSearchChange(e.target.value)} placeholder="Search contracts..." className="w-36 pl-5 pr-1.5 py-1 text-[10px] border border-gray-200 dark:border-navy-600 rounded bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400" />
          </div>
          <div className="relative">
            <button onClick={() => setShowFilterMenu(!showFilterMenu)} className="flex items-center gap-1 px-1.5 py-1 border border-gray-200 dark:border-navy-600 rounded text-[10px] text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors">
              <Filter className="w-2.5 h-2.5" /> Filters <ChevronDown className="w-2 h-2" />
            </button>
            {showFilterMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowFilterMenu(false)} />
                <div className="absolute right-0 top-full mt-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded shadow-lg z-20 py-0.5 w-44">
                  <div className="px-2 py-1 text-[8px] font-semibold text-gray-400 uppercase tracking-wider">Saved Filters</div>
                  {savedFilters.length === 0 ? <div className="px-2 py-1 text-[9px] text-gray-400 italic">No saved filters</div> : savedFilters.map(f => (
                    <button key={f.id} onClick={() => { onApplyFilter(f); setShowFilterMenu(false); }} className="w-full text-left px-2 py-0.5 text-[10px] text-navy-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-navy-700"><span className="font-medium">{f.name}</span></button>
                  ))}
                  <div className="border-t border-gray-100 dark:border-navy-700 mt-0.5 pt-0.5">
                    <button onClick={() => { onSaveCurrentFilter(); setShowFilterMenu(false); }} className="w-full text-left px-2 py-0.5 text-[10px] text-blue-600 hover:bg-gray-50 dark:hover:bg-navy-700 flex items-center gap-1"><Save className="w-2.5 h-2.5" /> Save Current Filter</button>
                  </div>
                </div>
              </>
            )}
          </div>
          <button onClick={onToggleCompact} className={`p-1 rounded transition-colors ${compactMode ? 'bg-gray-100 text-blue-600 dark:bg-navy-700 dark:text-blue-400' : 'text-gray-400 hover:text-navy-600 hover:bg-gray-100 dark:hover:bg-navy-700'}`} title={compactMode ? "Standard view" : "Compact view"}>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          {onToggleActivity && (
            <button onClick={onToggleActivity} className={`p-1 rounded transition-colors ${showActivity ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400' : 'text-gray-400 hover:text-navy-600 hover:bg-gray-100 dark:hover:bg-navy-700'}`} title="Activity feed">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

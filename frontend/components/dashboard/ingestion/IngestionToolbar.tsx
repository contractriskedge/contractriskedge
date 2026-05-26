"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Download, Link, FileJson, Repeat, Play, Pause,
  RefreshCw, ChevronDown, MoreHorizontal, Database, FileSpreadsheet,
  FolderOpen, Mail, Server, Cloud,
} from "lucide-react";
import type { ProcessingQueue } from "./types";

interface IngestionToolbarProps {
  queues: ProcessingQueue[];
  onUpload: (files: FileList | null) => void;
  onBulkImport: () => void;
  onConnectSource: () => void;
  onRetryFailed: () => void;
  onExportLogs: () => void;
  onPauseQueue: (queueId: string) => void;
  onResumeQueue: (queueId: string) => void;
}

export function IngestionToolbar({
  queues, onUpload, onBulkImport, onConnectSource, onRetryFailed, onExportLogs,
  onPauseQueue, onResumeQueue,
}: IngestionToolbarProps) {
  const [showQueueMenu, setShowQueueMenu] = useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpload(e.target.files);
    e.target.value = "";
  };

  const activeQueues = queues.filter(q => q.status === "active");
  const totalPending = queues.reduce((s, q) => s + q.pendingCount, 0);
  const totalProcessing = queues.reduce((s, q) => s + q.processingCount, 0);

  return (
    <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
      {/* Main Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5">
        <div className="flex items-center gap-1.5">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.tiff,.tif,.png,.jpg,.jpeg"
            onChange={handleFileChange}
            className="hidden"
          />
          <button onClick={handleUploadClick} className="flex items-center gap-1 px-3 py-1.5 bg-gold-500 hover:bg-gold-600 text-white rounded-lg text-[10px] font-medium transition-colors">
            <Upload className="w-3.5 h-3.5" /> Upload
          </button>
          <button onClick={onBulkImport} className="flex items-center gap-1 px-2.5 py-1.5 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg text-[10px] font-medium text-gray-600 dark:text-gray-300 transition-colors">
            <FolderOpen className="w-3.5 h-3.5" /> Bulk Import
          </button>
          <button onClick={onConnectSource} className="flex items-center gap-1 px-2.5 py-1.5 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg text-[10px] font-medium text-gray-600 dark:text-gray-300 transition-colors">
            <Link className="w-3.5 h-3.5" /> Connect
          </button>
          <div className="w-px h-5 bg-gray-200 dark:bg-navy-600 mx-1" />
          <button onClick={onRetryFailed} className="flex items-center gap-1 px-2.5 py-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg text-[10px] font-medium transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Retry Failed
          </button>
          <button onClick={onExportLogs} className="flex items-center gap-1 px-2.5 py-1.5 text-gray-500 hover:text-navy-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg text-[10px] font-medium transition-colors">
            <Download className="w-3.5 h-3.5" /> Export Logs
          </button>
        </div>

        {/* Queue Status */}
        <div className="relative">
          <button
            onClick={() => setShowQueueMenu(!showQueueMenu)}
            className="flex items-center gap-2 px-2.5 py-1.5 bg-gray-50 dark:bg-navy-900 border border-gray-200 dark:border-navy-600 rounded-lg text-[10px] hover:bg-gray-100 dark:hover:bg-navy-700 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-navy-900 dark:text-white font-medium tabular-nums">{activeQueues.length}</span>
              <span className="text-gray-500">queues active</span>
            </div>
            <div className="h-4 w-px bg-gray-200 dark:bg-navy-600" />
            <span className="text-amber-600 font-medium tabular-nums">{totalPending}</span>
            <span className="text-gray-500">pending</span>
            <span className="text-blue-600 font-medium tabular-nums">{totalProcessing}</span>
            <span className="text-gray-500">processing</span>
            <ChevronDown className="w-3 h-3 text-gray-400" />
          </button>
          <AnimatePresence>
            {showQueueMenu && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="absolute right-0 top-full mt-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-xl z-10 py-1 w-56"
              >
                {queues.map(q => (
                  <div key={q.id} className="px-3 py-1.5 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-navy-700">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${q.status === "active" ? "bg-green-500" : q.status === "paused" ? "bg-amber-400" : "bg-gray-400"}`} />
                      <span className="text-[10px] text-navy-900 dark:text-white">{q.name}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-[9px] text-gray-500 tabular-nums">{q.pendingCount}</span>
                      {q.status === "active" ? (
                        <button onClick={() => onPauseQueue(q.id)} className="p-0.5 text-gray-400 hover:text-amber-500"><Pause className="w-2.5 h-2.5" /></button>
                      ) : (
                        <button onClick={() => onResumeQueue(q.id)} className="p-0.5 text-gray-400 hover:text-green-500"><Play className="w-2.5 h-2.5" /></button>
                      )}
                    </div>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

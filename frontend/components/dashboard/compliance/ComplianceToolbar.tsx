"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Download, Shield, Play, ChevronDown, RefreshCw,
  FileText, Bell, SlidersHorizontal, MoreHorizontal, Eye,
  BarChart3, AlertTriangle, CheckCircle,
} from "lucide-react";
import type { ComplianceAudit } from "./types";

interface ComplianceToolbarProps {
  audits: ComplianceAudit[];
  onSearch: (query: string) => void;
  onExport: () => void;
  onRunScan: () => void;
  onAuditMode: () => void;
}

export function ComplianceToolbar({ audits, onSearch, onExport, onRunScan, onAuditMode }: ComplianceToolbarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [showAuditMenu, setShowAuditMenu] = useState(false);

  const activeAudits = audits.filter(a => a.status === "in_progress" || a.status === "scheduled");
  const overdueTasks = 8; // from mock data

  return (
    <div className="bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700">
      <div className="flex items-center justify-between px-3 py-1.5">
        <div className="flex items-center gap-1.5 flex-1">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input type="text" value={searchQuery} onChange={e => { setSearchQuery(e.target.value); onSearch(e.target.value); }}
              placeholder="Search regulations, findings, vendors..."
              className="w-full pl-8 pr-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gold-400"
            />
          </div>
          <button onClick={onRunScan} className="flex items-center gap-1 px-2.5 py-1.5 bg-gold-500 hover:bg-gold-600 text-white rounded-lg text-[10px] font-medium transition-colors">
            <RefreshCw className="w-3 h-3" /> Run Scan
          </button>
          <button onClick={onAuditMode} className="flex items-center gap-1 px-2.5 py-1.5 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg text-[10px] font-medium text-gray-600 dark:text-gray-300 transition-colors">
            <Eye className="w-3 h-3" /> Audit Mode
          </button>
          <div className="w-px h-5 bg-gray-200 dark:bg-navy-600 mx-1" />
          <button onClick={onExport} className="flex items-center gap-1 px-2.5 py-1.5 text-gray-500 hover:text-navy-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg text-[10px] font-medium transition-colors">
            <Download className="w-3 h-3" /> Export
          </button>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-2 ml-3">
          <div className="relative">
            <button onClick={() => setShowAuditMenu(!showAuditMenu)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-50 dark:bg-navy-900 border border-gray-200 dark:border-navy-600 rounded-lg text-[10px] hover:bg-gray-100 dark:hover:bg-navy-700 transition-colors">
              <Shield className="w-3 h-3 text-blue-500" />
              <span className="text-navy-900 dark:text-white font-medium tabular-nums">{activeAudits.length}</span>
              <span className="text-gray-500">active audits</span>
              <ChevronDown className="w-2.5 h-2.5 text-gray-400" />
            </button>
            <AnimatePresence>
              {showAuditMenu && (
                <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
                  className="absolute right-0 top-full mt-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-xl z-10 py-1 w-52">
                  {audits.map(a => (
                    <div key={a.id} className="px-3 py-1.5 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-navy-700">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${
                          a.status === "completed" ? "bg-green-500" : a.status === "in_progress" ? "bg-blue-500 animate-pulse" :
                          a.status === "scheduled" ? "bg-amber-400" : "bg-gray-400"
                        }`} />
                        <span className="text-[10px] text-navy-900 dark:text-white">{a.regulationName}</span>
                      </div>
                      <span className={`text-[8px] capitalize ${
                        a.status === "completed" ? "text-green-600" : a.status === "in_progress" ? "text-blue-600" : "text-gray-400"
                      }`}>{a.status.replace("_", " ")}</span>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          {overdueTasks > 0 && (
            <div className="flex items-center gap-1 px-2 py-1 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 rounded-lg text-[9px] text-red-600 font-medium">
              <AlertTriangle className="w-3 h-3" />
              {overdueTasks} overdue
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

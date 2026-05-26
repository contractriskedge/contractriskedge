"use client";

import React from "react";
import { motion } from "framer-motion";
import { Filter, RotateCcw } from "lucide-react";
import { OBLIGATION_TYPES } from "./types";

interface ObligationFilters {
  type: string; status: string; vendor: string; slaStatus: string; riskLevel: string; department: string;
}

interface FilterBarProps {
  filters: ObligationFilters;
  onChange: (key: keyof ObligationFilters, value: string) => void;
  onReset: () => void;
}

export function ObligationFilterBar({ filters, onChange, onReset }: FilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 flex-wrap bg-white rounded-lg border border-gray-200 shadow-sm px-3 py-2">
      <Filter className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      <select value={filters.type} onChange={(e) => onChange("type", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Type">
        <option value="">All Types</option>
        {OBLIGATION_TYPES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
      </select>
      <select value={filters.status} onChange={(e) => onChange("status", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Status">
        <option value="">All Status</option>
        <option value="pending">Pending</option><option value="in_progress">In Progress</option>
        <option value="overdue">Overdue</option><option value="escalated">Escalated</option><option value="completed">Completed</option>
      </select>
      <select value={filters.slaStatus} onChange={(e) => onChange("slaStatus", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="SLA">
        <option value="">SLA Status</option>
        <option value="on_track">On Track</option><option value="at_risk">At Risk</option><option value="breached">Breached</option>
      </select>
      <select value={filters.riskLevel} onChange={(e) => onChange("riskLevel", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Risk">
        <option value="">All Risk</option>
        <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option>
      </select>
      {activeCount > 0 && (
        <><span className="text-[10px] text-navy-600 font-medium bg-navy-50 px-1.5 py-0.5 rounded">{activeCount} active</span>
          <button onClick={onReset} className="text-[10px] text-gray-400 hover:text-red-500 flex items-center gap-0.5 transition-colors"><RotateCcw className="w-3 h-3" /> Reset</button>
        </>
      )}
    </motion.div>
  );
}

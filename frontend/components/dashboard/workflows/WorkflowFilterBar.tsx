"use client";

import React from "react";
import { motion } from "framer-motion";
import { Filter, RotateCcw } from "lucide-react";
import { WORKFLOW_STAGES } from "./types";

interface WorkflowFilters {
  stage: string; priority: string; slaStatus: string; riskLevel: string; department: string;
}

interface FilterBarProps {
  filters: WorkflowFilters;
  onChange: (key: keyof WorkflowFilters, value: string) => void;
  onReset: () => void;
}

export function WorkflowFilterBar({ filters, onChange, onReset }: FilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 flex-wrap bg-white rounded-lg border border-gray-200 shadow-sm px-3 py-2">
      <Filter className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      <select value={filters.stage} onChange={(e) => onChange("stage", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Stage">
        <option value="">All Stages</option>
        {WORKFLOW_STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
      </select>
      <select value={filters.priority} onChange={(e) => onChange("priority", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Priority">
        <option value="">All Priorities</option>
        <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
      </select>
      <select value={filters.slaStatus} onChange={(e) => onChange("slaStatus", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="SLA">
        <option value="">SLA Status</option>
        <option value="breached">Breached</option><option value="at_risk">At Risk</option><option value="on_track">On Track</option>
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

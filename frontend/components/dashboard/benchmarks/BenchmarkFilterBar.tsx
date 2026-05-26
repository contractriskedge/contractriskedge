"use client";

import React from "react";
import { motion } from "framer-motion";
import { Filter, RotateCcw } from "lucide-react";
import type { BenchmarkFilterState } from "./types";
import { INDUSTRIES, GEOGRAPHIES, CONTRACT_TYPES, REGULATIONS, CLAUSE_TYPES } from "./types";

interface BenchmarkFilterBarProps {
  filters: BenchmarkFilterState;
  onChange: (key: keyof BenchmarkFilterState, value: string) => void;
  onReset: () => void;
}

export function BenchmarkFilterBar({ filters, onChange, onReset }: BenchmarkFilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 flex-wrap bg-white rounded-lg border border-gray-200 shadow-sm px-3 py-2">
      <Filter className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      <select value={filters.industry} onChange={(e) => onChange("industry", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Industry">
        <option value="">All Industries</option>
        {INDUSTRIES.map((v) => <option key={v} value={v}>{v}</option>)}
      </select>
      <select value={filters.geography} onChange={(e) => onChange("geography", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Geography">
        <option value="">All Geographies</option>
        {GEOGRAPHIES.map((v) => <option key={v} value={v}>{v}</option>)}
      </select>
      <select value={filters.contractType} onChange={(e) => onChange("contractType", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Contract Type">
        <option value="">All Types</option>
        {CONTRACT_TYPES.map((v) => <option key={v} value={v}>{v}</option>)}
      </select>
      <select value={filters.clauseCategory} onChange={(e) => onChange("clauseCategory", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[120px]" aria-label="Clause Category">
        <option value="">All Clauses</option>
        {CLAUSE_TYPES.map((v) => <option key={v} value={v}>{v}</option>)}
      </select>
      <select value={filters.regulation} onChange={(e) => onChange("regulation", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Regulation">
        <option value="">All Regulations</option>
        {REGULATIONS.map((v) => <option key={v} value={v}>{v}</option>)}
      </select>
      {activeCount > 0 && (
        <><span className="text-[10px] text-navy-600 font-medium bg-navy-50 px-1.5 py-0.5 rounded">{activeCount} active</span>
          <button onClick={onReset} className="text-[10px] text-gray-400 hover:text-red-500 flex items-center gap-0.5 transition-colors"><RotateCcw className="w-3 h-3" /> Reset</button>
        </>
      )}
    </motion.div>
  );
}

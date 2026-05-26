"use client";

import React from "react";
import { motion } from "framer-motion";
import { Filter, RotateCcw } from "lucide-react";

interface AnalyticsFilters {
  businessUnit: string; geography: string; department: string; dateRange: string; riskLevel: string;
}

interface FilterBarProps {
  filters: AnalyticsFilters;
  onChange: (key: keyof AnalyticsFilters, value: string) => void;
  onReset: () => void;
}

export function AnalyticsFilterBar({ filters, onChange, onReset }: FilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 flex-wrap bg-white rounded-lg border border-gray-200 shadow-sm px-3 py-2">
      <Filter className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      <select value={filters.businessUnit} onChange={(e) => onChange("businessUnit", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="BU">
        <option value="">All Business Units</option>
        <option value="na">North America</option><option value="emea">EMEA</option><option value="apac">APAC</option><option value="latam">LATAM</option>
      </select>
      <select value={filters.geography} onChange={(e) => onChange("geography", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Geography">
        <option value="">All Geographies</option>
        <option value="us">United States</option><option value="eu">Europe</option><option value="apac">Asia Pacific</option><option value="latam">LATAM</option>
      </select>
      <select value={filters.department} onChange={(e) => onChange("department", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Department">
        <option value="">All Departments</option>
        <option value="engineering">Engineering</option><option value="legal">Legal</option><option value="finance">Finance</option><option value="procurement">Procurement</option>
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

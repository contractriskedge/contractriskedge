"use client";

import React from "react";
import { motion } from "framer-motion";
import { Filter, RotateCcw } from "lucide-react";
import type { GraphMode } from "./types";
import { GRAPH_MODES } from "./types";

interface GraphFilters {
  vendor: string; type: string; riskLevel: string;
}

interface GraphFilterBarProps {
  filters: GraphFilters;
  onChange: (key: keyof GraphFilters, value: string) => void;
  onReset: () => void;
  mode: GraphMode;
  onModeChange: (mode: GraphMode) => void;
}

const VENDORS = ["Acme Corp", "GlobalTech Inc", "DataSync Partners", "CloudServ Ltd", "SecureNet Solutions", "InnoVate LLC", "Pacific Rim Trading", "EuroLegal Partners"];
const TYPES = ["master_service_agreement", "amendment", "statement_of_work", "dpa", "nda", "license", "vendor", "obligation", "insurance"];

export function GraphFilterBar({ filters, onChange, onReset, mode, onModeChange }: GraphFilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
      {/* Graph mode selector */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {GRAPH_MODES.map((gm) => (
          <button key={gm.id} onClick={() => onModeChange(gm.id)}
            className={`text-[10px] font-medium px-2.5 py-1.5 rounded-lg whitespace-nowrap transition-all ${
              mode === gm.id ? "bg-navy-700 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`} title={gm.description}>
            {gm.label}
          </button>
        ))}
      </div>
      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap bg-white rounded-lg border border-gray-200 shadow-sm px-3 py-2">
        <Filter className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
        <select value={filters.vendor} onChange={(e) => onChange("vendor", e.target.value)}
          className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Vendor">
          <option value="">All Vendors</option>
          {VENDORS.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={filters.type} onChange={(e) => onChange("type", e.target.value)}
          className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Type">
          <option value="">All Types</option>
          {TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <select value={filters.riskLevel} onChange={(e) => onChange("riskLevel", e.target.value)}
          className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Risk">
          <option value="">All Risk</option>
          <option value="critical">Critical</option><option value="high">High+</option><option value="medium">Medium+</option>
        </select>
        {activeCount > 0 && (
          <><span className="text-[10px] text-navy-600 font-medium bg-navy-50 px-1.5 py-0.5 rounded">{activeCount} active</span>
            <button onClick={onReset} className="text-[10px] text-gray-400 hover:text-red-500 flex items-center gap-0.5 transition-colors"><RotateCcw className="w-3 h-3" /> Reset</button>
          </>
        )}
      </div>
    </motion.div>
  );
}

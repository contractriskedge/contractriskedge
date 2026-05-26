"use client";

import React from "react";
import { motion } from "framer-motion";
import { Filter, RotateCcw } from "lucide-react";

interface ProcurementFilters {
  category: string; geography: string; riskLevel: string; spendRange: string;
  complianceStatus: string; owner: string; businessUnit: string;
}

interface FilterBarProps {
  filters: ProcurementFilters;
  onChange: (key: keyof ProcurementFilters, value: string) => void;
  onReset: () => void;
}

const CATEGORIES = ["Cloud Services", "Software Licensing", "Professional Services", "Hardware", "Consulting", "Marketing", "Logistics", "Facilities"];
const GEOGRAPHIES = ["United States", "Germany", "Japan", "United Kingdom", "Canada", "India", "France", "Singapore"];
const OWNERS = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson"];
const UNITS = ["North America", "EMEA", "APAC", "LATAM"];

function FS({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label={label}>
      <option value="">{label}</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

export function ProcurementFilterBar({ filters, onChange, onReset }: FilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 flex-wrap bg-white rounded-lg border border-gray-200 shadow-sm px-3 py-2">
      <Filter className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      <FS label="Category" value={filters.category} options={CATEGORIES} onChange={(v) => onChange("category", v)} />
      <FS label="Geography" value={filters.geography} options={GEOGRAPHIES} onChange={(v) => onChange("geography", v)} />
      <select value={filters.riskLevel} onChange={(e) => onChange("riskLevel", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Risk Level">
        <option value="">Risk Level</option>
        <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
      </select>
      <select value={filters.complianceStatus} onChange={(e) => onChange("complianceStatus", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Compliance">
        <option value="">Compliance</option>
        <option value="compliant">Compliant</option><option value="at_risk">At Risk</option><option value="non_compliant">Non-Compliant</option>
      </select>
      <FS label="Owner" value={filters.owner} options={OWNERS} onChange={(v) => onChange("owner", v)} />
      <FS label="Business Unit" value={filters.businessUnit} options={UNITS} onChange={(v) => onChange("businessUnit", v)} />
      {activeCount > 0 && (
        <><span className="text-[10px] text-navy-600 font-medium bg-navy-50 px-1.5 py-0.5 rounded">{activeCount} active</span>
          <button onClick={onReset} className="text-[10px] text-gray-400 hover:text-red-500 flex items-center gap-0.5 transition-colors"><RotateCcw className="w-3 h-3" /> Reset</button>
        </>
      )}
    </motion.div>
  );
}

"use client";

import React from "react";
import { motion } from "framer-motion";
import { Filter, RotateCcw } from "lucide-react";

interface AdminFilters {
  tenant: string; userRole: string; complianceStatus: string;
  integrationType: string; auditSeverity: string; aiModel: string;
}

interface FilterBarProps {
  filters: AdminFilters;
  onChange: (key: keyof AdminFilters, value: string) => void;
  onReset: () => void;
}

export function AdminFilterBar({ filters, onChange, onReset }: FilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 flex-wrap bg-white rounded-lg border border-gray-200 shadow-sm px-3 py-2">
      <Filter className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      <select value={filters.tenant} onChange={(e) => onChange("tenant", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors min-w-[100px]" aria-label="Tenant">
        <option value="">All Tenants</option>
        <option value="acme">Acme Corp</option><option value="globaltech">GlobalTech Inc</option><option value="securenet">SecureNet Solutions</option>
      </select>
      <select value={filters.userRole} onChange={(e) => onChange("userRole", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Role">
        <option value="">All Roles</option>
        <option value="admin">Admin</option><option value="legal">Legal Counsel</option><option value="analyst">Contract Analyst</option><option value="procurement">Procurement</option><option value="compliance">Compliance</option>
      </select>
      <select value={filters.complianceStatus} onChange={(e) => onChange("complianceStatus", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Compliance">
        <option value="">Compliance</option>
        <option value="compliant">Compliant</option><option value="non_compliant">Non-Compliant</option><option value="in_progress">In Progress</option>
      </select>
      <select value={filters.auditSeverity} onChange={(e) => onChange("auditSeverity", e.target.value)} className="text-[11px] border border-gray-200 rounded-md px-2 py-1.5 text-gray-600 bg-white hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors" aria-label="Severity">
        <option value="">Audit Severity</option>
        <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
      </select>
      {activeCount > 0 && (
        <><span className="text-[10px] text-navy-600 font-medium bg-navy-50 px-1.5 py-0.5 rounded">{activeCount} active</span>
          <button onClick={onReset} className="text-[10px] text-gray-400 hover:text-red-500 flex items-center gap-0.5 transition-colors"><RotateCcw className="w-3 h-3" /> Reset</button>
        </>
      )}
    </motion.div>
  );
}

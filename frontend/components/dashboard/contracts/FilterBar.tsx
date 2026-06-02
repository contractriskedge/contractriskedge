"use client";

import React from "react";
import { motion } from "framer-motion";
import { Filter, X, RotateCcw } from "lucide-react";
import type { ContractFilterState } from "./types";

interface FilterBarProps {
  filters: ContractFilterState;
  onChange: (key: keyof ContractFilterState, value: string) => void;
  onReset: () => void;
}

const VENDORS = ["Acme Corp", "GlobalTech Inc", "DataSync Partners", "CloudServ Ltd", "SecureNet Solutions", "InnoVate LLC", "Pacific Rim Trading", "EuroLegal Partners"];
const GEOGRAPHIES = ["United States", "Germany", "Japan", "United Kingdom", "Canada", "Australia", "France", "Singapore"];
const CONTRACT_TYPES = ["MSA", "SOW", "NDA", "License", "Service Agreement", "Partnership", "Employment", "Lease", "SaaS Agreement", "Consulting"];
const BUSINESS_UNITS = ["North America", "EMEA", "APAC", "LATAM"];
const OWNERS = ["Alice Chen", "Bob Martinez", "Carol Singh", "David Kim", "Eve Johnson", "Frank Wilson", "Grace Lee", "Henry Park"];
const WORKFLOW_STAGES = ["Draft", "Review", "Approval", "Negotiation", "Executed", "Renewal", "Archived"];

function FilterSelect({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors min-w-[100px]"
      aria-label={label}>
      <option value="">{label}</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

export function FilterBar({ filters, onChange, onReset }: FilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;

  return (
    <div className="flex items-center gap-2 flex-wrap bg-white dark:bg-navy-800 rounded-lg border border-gray-200 dark:border-navy-700 px-3 py-1.5">
      <Filter className="w-3 h-3 text-gray-400 flex-shrink-0" />
      <FilterSelect label="Vendor" value={filters.vendor} options={VENDORS} onChange={(v) => onChange("vendor", v)} />
      <FilterSelect label="Geography" value={filters.geography} options={GEOGRAPHIES} onChange={(v) => onChange("geography", v)} />
      <FilterSelect label="Type" value={filters.contractType} options={CONTRACT_TYPES} onChange={(v) => onChange("contractType", v)} />
      <FilterSelect label="Business Unit" value={filters.businessUnit} options={BUSINESS_UNITS} onChange={(v) => onChange("businessUnit", v)} />
      <FilterSelect label="Owner" value={filters.owner} options={OWNERS} onChange={(v) => onChange("owner", v)} />
      <select value={filters.riskLevel} onChange={(e) => onChange("riskLevel", e.target.value)}
        className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors" aria-label="Risk Level">
        <option value="">Risk Level</option>
        <option value="critical">Critical</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>
      <select value={filters.status} onChange={(e) => onChange("status", e.target.value)}
        className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors" aria-label="Status">
        <option value="">Status</option>
        <option value="active">Active</option>
        <option value="expiring_soon">Expiring Soon</option>
        <option value="under_review">Under Review</option>
        <option value="pending_signature">Pending Signature</option>
        <option value="expired">Expired</option>
      </select>
      <select value={filters.workflowStage} onChange={(e) => onChange("workflowStage", e.target.value)}
        className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors" aria-label="Workflow Stage">
        <option value="">Workflow</option>
        {WORKFLOW_STAGES.map((s) => <option key={s} value={s.toLowerCase()}>{s}</option>)}
      </select>
      {activeCount > 0 && (
        <>
          <span className="text-[10px] text-blue-600 dark:text-blue-400 font-medium bg-blue-50 dark:bg-blue-900/20 px-1.5 py-0.5 rounded">{activeCount} active</span>
          <button onClick={onReset} className="text-[10px] text-gray-400 hover:text-red-500 dark:hover:text-red-400 flex items-center gap-0.5 transition-colors">
            <RotateCcw className="w-3 h-3" /> Reset
          </button>
        </>
      )}
    </div>
  );
}

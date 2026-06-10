"use client";

import React, { useMemo } from "react";
import { Filter, RotateCcw } from "lucide-react";
import type { ContractFilterState, ContractRecord } from "./types";

interface FilterBarProps {
  filters: ContractFilterState;
  onChange: (key: keyof ContractFilterState, value: string) => void;
  onReset: () => void;
  /** All contracts in the repository — used to derive dynamic facet options. */
  allContracts: ContractRecord[];
}

function uniqueValues<T>(arr: T[]): T[] {
  return Array.from(new Set(arr.filter((v) => v !== undefined && v !== null && v !== "")));
}

function FilterSelect({
  label, value, options, counts, onChange,
}: {
  label: string;
  value: string;
  options: string[];
  counts?: Record<string, number>;
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors pr-6 appearance-none cursor-pointer min-w-[100px]"
      aria-label={label}
    >
      <option value="">{label}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}{counts ? ` (${counts[o] || 0})` : ""}
        </option>
      ))}
    </select>
  );
}

export function FilterBar({ filters, onChange, onReset, allContracts }: FilterBarProps) {
  const activeCount = Object.values(filters).filter((v) => v !== "").length;

  // Derive dynamic facet values from the live contract set so the dropdown
  // options always reflect real data — and the counts always match what
  // the user will see in the table once the filter is applied.
  const facets = useMemo(() => {
    const vendors = uniqueValues(allContracts.map((c) => c.vendor));
    const geographies = uniqueValues(allContracts.map((c) => c.geography));
    const contractTypes = uniqueValues(allContracts.map((c) => c.contractType));
    const businessUnits = uniqueValues(allContracts.map((c) => c.businessUnit));
    const owners = uniqueValues(allContracts.map((c) => c.owner));

    // Counts: how many contracts have each facet value.
    const countFor = (key: keyof ContractRecord) => {
      const counts: Record<string, number> = {};
      for (const c of allContracts) {
        const v = c[key] as unknown as string;
        if (!v) continue;
        counts[v] = (counts[v] || 0) + 1;
      }
      return counts;
    };

    return {
      vendors,
      geographies,
      contractTypes,
      businessUnits,
      owners,
      counts: {
        vendor: countFor("vendor"),
        geography: countFor("geography"),
        contractType: countFor("contractType"),
        businessUnit: countFor("businessUnit"),
        owner: countFor("owner"),
      },
    };
  }, [allContracts]);

  return (
    <div className="flex items-center gap-2 flex-wrap bg-white dark:bg-navy-800 rounded-lg border border-gray-200 dark:border-navy-700 px-3 py-1.5">
      <Filter className="w-3 h-3 text-gray-400 flex-shrink-0" />
      <FilterSelect label="Vendor" value={filters.vendor} options={facets.vendors} counts={facets.counts.vendor} onChange={(v) => onChange("vendor", v)} />
      <FilterSelect label="Geography" value={filters.geography} options={facets.geographies} counts={facets.counts.geography} onChange={(v) => onChange("geography", v)} />
      <FilterSelect label="Type" value={filters.contractType} options={facets.contractTypes} counts={facets.counts.contractType} onChange={(v) => onChange("contractType", v)} />
      <FilterSelect label="Business Unit" value={filters.businessUnit} options={facets.businessUnits} counts={facets.counts.businessUnit} onChange={(v) => onChange("businessUnit", v)} />
      <FilterSelect label="Owner" value={filters.owner} options={facets.owners} counts={facets.counts.owner} onChange={(v) => onChange("owner", v)} />
      <select value={filters.riskLevel} onChange={(e) => onChange("riskLevel", e.target.value)}
        className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors cursor-pointer" aria-label="Risk Level">
        <option value="">Risk Level</option>
        <option value="critical">Critical (8+)</option>
        <option value="high">High (6-8)</option>
        <option value="medium">Medium (4-6)</option>
        <option value="low">Low (&lt;4)</option>
      </select>
      <select value={filters.status} onChange={(e) => onChange("status", e.target.value)}
        className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors cursor-pointer" aria-label="Status">
        <option value="">Status</option>
        <option value="active">Active</option>
        <option value="expiring_soon">Expiring Soon</option>
        <option value="under_review">Under Review</option>
        <option value="expired">Expired</option>
        <option value="draft">Draft</option>
      </select>
      <select value={filters.workflowStage} onChange={(e) => onChange("workflowStage", e.target.value)}
        className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 dark:hover:border-navy-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors cursor-pointer" aria-label="Workflow Stage">
        <option value="">Workflow</option>
        <option value="intake">Intake</option>
        <option value="ai_review">AI Review</option>
        <option value="review">Review</option>
        <option value="procurement">Procurement</option>
        <option value="legal_ops">Legal Ops</option>
        <option value="security">Security</option>
        <option value="negotiation">Negotiation</option>
        <option value="executive">Executive</option>
        <option value="executed">Executed</option>
        <option value="archived">Archived</option>
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

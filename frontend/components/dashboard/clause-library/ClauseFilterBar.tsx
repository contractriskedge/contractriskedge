/**
 * ClauseFilterBar — secondary filter strip for the Clause Library.
 *
 * Filters supported (per the audit checklist):
 *   - Clause Type (free text)
 *   - Risk (critical / high / medium / low / info)
 *   - Jurisdiction
 *   - Status (approved / pending_review / deprecated / draft)
 *   - Template
 *   - Mandatory (yes / no / all)
 *   - Custom
 *
 * Counts shown next to each option reflect the currently filtered data set,
 * so the UI re-balances as users narrow down.
 */

"use client";

import React from "react";
import { X, Filter as FilterIcon } from "lucide-react";

export interface ClauseFilters {
  clauseType: string;
  risk: string;
  jurisdiction: string;
  status: string;
  template: string;
  mandatory: "all" | "yes" | "no";
  custom: string;
}

export const EMPTY_FILTERS: ClauseFilters = {
  clauseType: "",
  risk: "",
  jurisdiction: "",
  status: "",
  template: "",
  mandatory: "all",
  custom: "",
};

export interface FilterOption {
  value: string;
  label: string;
  count: number;
}

interface ClauseFilterBarProps {
  filters: ClauseFilters;
  onChange: (next: ClauseFilters) => void;
  onReset: () => void;
  riskOptions: FilterOption[];
  jurisdictionOptions: FilterOption[];
  statusOptions: FilterOption[];
  templateOptions: FilterOption[];
  totalShown: number;
  totalAll: number;
}

const inputBase =
  "text-[10px] px-2 py-1.5 rounded-md border border-gray-200 bg-white text-navy-900 focus:outline-none focus:ring-1 focus:ring-navy-400";

export function ClauseFilterBar({
  filters,
  onChange,
  onReset,
  riskOptions,
  jurisdictionOptions,
  statusOptions,
  templateOptions,
  totalShown,
  totalAll,
}: ClauseFilterBarProps) {
  const set = <K extends keyof ClauseFilters>(key: K, value: ClauseFilters[K]) =>
    onChange({ ...filters, [key]: value });

  const activeCount = [
    filters.clauseType,
    filters.risk,
    filters.jurisdiction,
    filters.status,
    filters.template,
    filters.mandatory !== "all" ? filters.mandatory : "",
    filters.custom,
  ].filter(Boolean).length;

  return (
    <div
      data-testid="clause-filter-bar"
      className="bg-white border border-gray-200 rounded-lg px-3 py-2 flex flex-wrap items-center gap-2 shadow-sm"
    >
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
        <FilterIcon className="w-3 h-3" /> Filter
      </span>

      <input
        type="text"
        value={filters.clauseType}
        onChange={(e) => set("clauseType", e.target.value)}
        placeholder="Clause type…"
        aria-label="Filter by clause type"
        className={`${inputBase} w-32`}
      />

      <select
        value={filters.risk}
        onChange={(e) => set("risk", e.target.value)}
        aria-label="Filter by risk"
        className={inputBase}
      >
        <option value="">Risk (all)</option>
        {riskOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label} ({o.count})
          </option>
        ))}
      </select>

      <select
        value={filters.jurisdiction}
        onChange={(e) => set("jurisdiction", e.target.value)}
        aria-label="Filter by jurisdiction"
        className={inputBase}
      >
        <option value="">Jurisdiction (all)</option>
        {jurisdictionOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label} ({o.count})
          </option>
        ))}
      </select>

      <select
        value={filters.status}
        onChange={(e) => set("status", e.target.value)}
        aria-label="Filter by status"
        className={inputBase}
      >
        <option value="">Status (all)</option>
        {statusOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label} ({o.count})
          </option>
        ))}
      </select>

      <select
        value={filters.template}
        onChange={(e) => set("template", e.target.value)}
        aria-label="Filter by template"
        className={inputBase}
      >
        <option value="">Template (all)</option>
        {templateOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label} ({o.count})
          </option>
        ))}
      </select>

      <select
        value={filters.mandatory}
        onChange={(e) => set("mandatory", e.target.value as ClauseFilters["mandatory"])}
        aria-label="Filter by mandatory"
        className={inputBase}
      >
        <option value="all">Mandatory (all)</option>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>

      <input
        type="text"
        value={filters.custom}
        onChange={(e) => set("custom", e.target.value)}
        placeholder="Custom tag…"
        aria-label="Filter by custom tag"
        className={`${inputBase} w-28`}
      />

      {activeCount > 0 ? (
        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center gap-1 text-[10px] font-medium text-gray-500 hover:text-red-600 transition-colors"
          aria-label="Clear filters"
        >
          <X className="w-3 h-3" /> Clear ({activeCount})
        </button>
      ) : null}

      <span className="ml-auto text-[10px] text-gray-400 tabular-nums">
        {totalShown} of {totalAll} clauses
      </span>
    </div>
  );
}

/**
 * Compute a count of clauses matching each option for a given field. Used
 * to populate the dropdowns so the counts reflect the *current* filter set
 * (excluding the field being counted, to avoid zero-everywhere).
 */
export function countBy<T, K extends keyof T>(
  items: T[],
  key: K,
  transform?: (v: T[K]) => string,
): Map<string, number> {
  const out = new Map<string, number>();
  for (const it of items) {
    const raw = it[key];
    const k = transform ? transform(raw) : String(raw ?? "");
    if (!k) continue;
    out.set(k, (out.get(k) ?? 0) + 1);
  }
  return out;
}

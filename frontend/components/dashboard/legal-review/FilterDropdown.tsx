"use client";

import React from "react";
import { Filter, ChevronDown } from "lucide-react";

interface FilterOption {
  value: string;
  label: string;
}

interface FilterDropdownProps {
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (value: string) => void;
  className?: string;
}

export function FilterDropdown({ label, value, options, onChange, className = "" }: FilterDropdownProps) {
  const selectedLabel = options.find((o) => o.value === value)?.label || label;

  return (
    <div className={`relative ${className}`}>
      <label className="sr-only">{label}</label>
      <div className="relative">
        <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" aria-hidden="true" />
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none pl-8 pr-7 py-1.5 text-xs border border-gray-200 rounded-lg bg-white text-gray-700 hover:border-gray-300 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 transition-colors cursor-pointer"
          aria-label={`Filter by ${label}`}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" aria-hidden="true" />
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Filter, Bookmark, Clock, Search, Brain, Sparkles, Layers, GitMerge,
  ChevronDown, ChevronRight, Plus, Bell, Trash2, AlertTriangle,
  FileText, FileSearch, ClipboardCheck, Building2, Workflow,
  GitMerge as GitMergeIcon, BarChart3, ScrollText, SlidersHorizontal,
  X, RotateCcw,
} from "lucide-react";
import type { SearchCategory, SavedSearch, SearchFilter, FilterCategory } from "./types";
import { mockSearchCategories, mockSavedSearches } from "./mockData";

interface SearchLeftSidebarProps {
  categories: SearchCategory[];
  activeCategory: string;
  onCategoryChange: (id: string) => void;
  filters: SearchFilter[];
  onFilterAdd: (filter: SearchFilter) => void;
  onFilterRemove: (filterId: string) => void;
  onClearFilters: () => void;
  savedSearches: SavedSearch[];
  onSavedSearchSelect: (saved: SavedSearch) => void;
}

const categoryIcons: Record<string, React.ReactNode> = {
  all: <Search className="w-3.5 h-3.5" />,
  contracts: <FileText className="w-3.5 h-3.5" />,
  clauses: <FileSearch className="w-3.5 h-3.5" />,
  obligations: <ClipboardCheck className="w-3.5 h-3.5" />,
  vendors: <Building2 className="w-3.5 h-3.5" />,
  workflows: <Workflow className="w-3.5 h-3.5" />,
  negotiations: <GitMergeIcon className="w-3.5 h-3.5" />,
  benchmarks: <BarChart3 className="w-3.5 h-3.5" />,
  audit: <ScrollText className="w-3.5 h-3.5" />,
};

const filterOptions: { category: FilterCategory; label: string; options: { value: string; label: string }[] }[] = [
  { category: "contract_type", label: "Contract Type", options: [
    { value: "msa", label: "MSA" }, { value: "sla", label: "SLA" }, { value: "dpa", label: "DPA" },
    { value: "nda", label: "NDA" }, { value: "license", label: "License" }, { value: "amendment", label: "Amendment" },
  ]},
  { category: "risk_level", label: "Risk Level", options: [
    { value: "critical", label: "Critical" }, { value: "high", label: "High" },
    { value: "medium", label: "Medium" }, { value: "low", label: "Low" },
  ]},
  { category: "clause_category", label: "Clause Category", options: [
    { value: "liability", label: "Liability" }, { value: "indemnification", label: "Indemnification" },
    { value: "termination", label: "Termination" }, { value: "data_privacy", label: "Data Privacy" },
    { value: "sla", label: "SLA" }, { value: "ip", label: "IP Rights" },
  ]},
  { category: "compliance_category", label: "Compliance", options: [
    { value: "gdpr", label: "GDPR" }, { value: "ccpa", label: "CCPA" },
    { value: "soc2", label: "SOC 2" }, { value: "iso27001", label: "ISO 27001" },
    { value: "hipaa", label: "HIPAA" },
  ]},
  { category: "geography", label: "Geography", options: [
    { value: "us", label: "United States" }, { value: "eu", label: "European Union" },
    { value: "uk", label: "United Kingdom" }, { value: "germany", label: "Germany" },
    { value: "asia", label: "Asia Pacific" },
  ]},
  { category: "workflow_stage", label: "Workflow Stage", options: [
    { value: "drafting", label: "Drafting" }, { value: "review", label: "Review" },
    { value: "negotiating", label: "Negotiating" }, { value: "approved", label: "Approved" },
    { value: "executed", label: "Executed" },
  ]},
];

export function SearchLeftSidebar({
  categories, activeCategory, onCategoryChange,
  filters, onFilterAdd, onFilterRemove, onClearFilters,
  savedSearches, onSavedSearchSelect,
}: SearchLeftSidebarProps) {
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [expandedFilters, setExpandedFilters] = useState<Set<string>>(new Set(["risk_level"]));

  const toggleFilter = (cat: string) => {
    setExpandedFilters(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const activeFilterValues = new Set(filters.map(f => f.value));

  return (
    <div className="w-64 flex-shrink-0 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-navy-900 dark:text-white">Discovery</h3>
          <button
            onClick={() => setShowFilterPanel(!showFilterPanel)}
            className={`p-1 rounded transition-colors ${showFilterPanel ? "bg-gold-100 text-gold-600 dark:bg-gold-900/20 dark:text-gold-400" : "text-gray-400 hover:text-navy-600 dark:hover:text-gray-300"}`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Search Categories */}
        <div className="px-2 py-2 space-y-0.5">
          <span className="text-[9px] font-semibold text-gray-400 uppercase tracking-wider px-2 py-1">Categories</span>
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => onCategoryChange(cat.id)}
              className={`w-full text-left px-2 py-1.5 rounded-lg flex items-center gap-2 transition-colors ${
                activeCategory === cat.id
                  ? "bg-gold-50 text-gold-700 dark:bg-gold-900/20 dark:text-gold-400"
                  : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700"
              }`}
            >
              <span className={activeCategory === cat.id ? "text-gold-500" : "text-gray-400"}>{categoryIcons[cat.id]}</span>
              <span className="text-[11px] font-medium flex-1 truncate">{cat.label}</span>
              <span className={`text-[9px] tabular-nums ${activeCategory === cat.id ? "text-gold-500" : "text-gray-400"}`}>{cat.count.toLocaleString()}</span>
            </button>
          ))}
        </div>

        {/* Active Filters */}
        {filters.length > 0 && (
          <div className="px-2 py-2 border-t border-gray-100 dark:border-navy-700">
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-[9px] font-semibold text-gray-400 uppercase tracking-wider">Active Filters</span>
              <button onClick={onClearFilters} className="text-[9px] text-gold-600 hover:text-gold-700 flex items-center gap-0.5">
                <RotateCcw className="w-2.5 h-2.5" /> Clear
              </button>
            </div>
            <div className="flex flex-wrap gap-1 px-1">
              {filters.map(f => (
                <span key={f.id} className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gold-50 dark:bg-gold-900/20 text-gold-700 dark:text-gold-400 rounded-full text-[9px] font-medium">
                  {f.label}: {f.value}
                  <button onClick={() => onFilterRemove(f.id)} className="hover:text-gold-900 dark:hover:text-gold-200">
                    <X className="w-2.5 h-2.5" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Filter Panel (expandable) */}
        <AnimatePresence>
          {showFilterPanel && (
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: "auto" }}
              exit={{ height: 0 }}
              className="overflow-hidden border-t border-gray-100 dark:border-navy-700"
            >
              <div className="px-2 py-2 space-y-1">
                <span className="text-[9px] font-semibold text-gray-400 uppercase tracking-wider px-2 py-1">Add Filters</span>
                {filterOptions.map(fg => (
                  <div key={fg.category} className="border border-gray-100 dark:border-navy-700 rounded-lg overflow-hidden">
                    <button
                      onClick={() => toggleFilter(fg.category)}
                      className="w-full text-left px-2.5 py-1.5 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors text-[11px] font-medium text-navy-900 dark:text-white"
                    >
                      {fg.label}
                      {expandedFilters.has(fg.category) ? <ChevronDown className="w-3 h-3 text-gray-400" /> : <ChevronRight className="w-3 h-3 text-gray-400" />}
                    </button>
                    <AnimatePresence>
                      {expandedFilters.has(fg.category) && (
                        <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
                          <div className="px-2 pb-1.5 space-y-0.5">
                            {fg.options.map(opt => {
                              const isActive = activeFilterValues.has(opt.value);
                              return (
                                <button
                                  key={opt.value}
                                  onClick={() => {
                                    if (isActive) {
                                      const existing = filters.find(f => f.value === opt.value);
                                      if (existing) onFilterRemove(existing.id);
                                    } else {
                                      onFilterAdd({ id: `f-${opt.value}`, category: fg.category, label: fg.label, value: opt.value });
                                    }
                                  }}
                                  className={`w-full text-left px-2 py-1 rounded text-[10px] transition-colors flex items-center justify-between ${
                                    isActive ? "bg-gold-50 text-gold-700 dark:bg-gold-900/20 dark:text-gold-400" : "text-gray-500 hover:text-navy-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700"
                                  }`}
                                >
                                  {opt.label}
                                  {isActive && <X className="w-2.5 h-2.5" />}
                                </button>
                              );
                            })}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Saved Searches */}
        <div className="px-2 py-2 border-t border-gray-100 dark:border-navy-700">
          <div className="flex items-center justify-between px-2 py-1">
            <span className="text-[9px] font-semibold text-gray-400 uppercase tracking-wider">Saved Searches</span>
            <button className="text-[9px] text-gold-600 hover:text-gold-700">
              <Plus className="w-2.5 h-2.5" />
            </button>
          </div>
          <div className="space-y-0.5">
            {savedSearches.map(ss => (
              <button
                key={ss.id}
                onClick={() => onSavedSearchSelect(ss)}
                className="w-full text-left px-2 py-1.5 rounded-lg flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors group"
              >
                <Bookmark className="w-3 h-3 text-gold-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-[11px] font-medium text-navy-900 dark:text-white truncate block">{ss.name}</span>
                  <span className="text-[9px] text-gray-400 truncate block">{ss.query}</span>
                </div>
                {ss.alertEnabled && <Bell className="w-2.5 h-2.5 text-rose-400 flex-shrink-0" />}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

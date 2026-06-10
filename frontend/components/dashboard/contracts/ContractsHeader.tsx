"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Sparkles, ChevronDown, Clock, Star, X, Filter, Download } from "lucide-react";
import type { SavedView } from "./types";

const SUGGESTIONS = [
  "Show contracts with uncapped liability",
  "Find NDAs expiring in 60 days",
  "Contracts missing DPA clauses",
  "High-risk agreements over $1M",
  "Vendors with auto-renewal risk",
];

interface ContractsHeaderProps {
  search: string;
  onSearchChange: (v: string) => void;
  savedViews: SavedView[];
  activeViewId: string;
  onViewChange: (id: string) => void;
  resultCount: number;
}

export function ContractsHeader({
  search, onSearchChange, savedViews, activeViewId, onViewChange, resultCount,
}: ContractsHeaderProps) {
  const [focused, setFocused] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showViews, setShowViews] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (suggestionRef.current && !suggestionRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const activeView = savedViews.find((v) => v.id === activeViewId);

  return (
    <div className="space-y-2 px-3">
      {/* Search + Filters row */}
      <div className="flex items-center gap-2">
        {/* Smart search */}
        <div className="relative flex-1" ref={suggestionRef}>
          <div className={`flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-navy-800 border rounded-lg transition-all ${
            focused ? "border-blue-400 shadow-sm ring-1 ring-blue-400/20" : "border-gray-200 dark:border-navy-600 hover:border-gray-300 dark:hover:border-navy-500"
          }`}>
            <Search className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            <input ref={inputRef} type="text" value={search} onChange={(e) => onSearchChange(e.target.value)}
              onFocus={() => { setFocused(true); setShowSuggestions(true); }} onBlur={() => setFocused(false)}
              placeholder='Search contracts...'
              className="flex-1 text-[11px] text-gray-700 dark:text-gray-200 placeholder-gray-400 bg-transparent border-none outline-none focus:ring-0 p-0"
              aria-label="Search contracts" />
            {search && (
              <button onClick={() => { onSearchChange(""); inputRef.current?.focus(); }} className="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400">
                <X className="w-3 h-3" />
              </button>
            )}
            <Sparkles className="w-3.5 h-3.5 text-gold-400 flex-shrink-0" aria-label="AI-powered search" />
          </div>

          {/* Suggestions dropdown */}
          <AnimatePresence>
            {showSuggestions && !search && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-2"
              >
                <p className="px-3 py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Try searching</p>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => { onSearchChange(s); setShowSuggestions(false); }}
                    className="w-full text-left px-3 py-1.5 text-xs text-gray-600 hover:bg-navy-50 flex items-center gap-2 transition-colors"
                  >
                    <Sparkles className="w-3 h-3 text-gold-400 flex-shrink-0" />
                    {s}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Saved views */}
        <div className="relative">
          <button
            onClick={() => setShowViews(!showViews)}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <Star className="w-3.5 h-3.5" />
            {activeView?.name || "Views"}
            <ChevronDown className="w-3 h-3" />
          </button>
          <AnimatePresence>
            {showViews && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1"
              >
                {savedViews.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => { onViewChange(v.id); setShowViews(false); }}
                    className={`w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 transition-colors ${
                      v.id === activeViewId ? "bg-navy-50 text-navy-700 font-medium" : "text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    <Star className={`w-3 h-3 ${v.isDefault ? "text-gold-400" : "text-gray-300"}`} />
                    {v.name}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Export */}
        <button
          onClick={() => {
            // Trigger a CSV download of the current filtered set
            const ev = new CustomEvent("contracts:export-csv", { detail: { search, filters: (window as any).__contractsPageFilters } });
            window.dispatchEvent(ev);
          }}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <Download className="w-3.5 h-3.5" />
          Export
        </button>

        {/* Result count */}
        <span data-testid="result-count" className="text-[11px] text-gray-400 tabular-nums whitespace-nowrap">{resultCount} results</span>
      </div>
    </div>
  );
}

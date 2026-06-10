"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Sparkles, X, Clock, TrendingUp, ChevronDown, Mic,
  Filter, SlidersHorizontal, ArrowRight, History, Bookmark,
  Brain, Layers, GitMerge, Loader2, Bell,
} from "lucide-react";
import type { SearchMode } from "./types";

const searchModeLabels: Record<string, { label: string; description: string }> = {
  semantic: { label: "AI Semantic", description: "AI-powered semantic search across all content" },
  keyword: { label: "Keyword", description: "Exact keyword and phrase matching" },
  hybrid: { label: "Hybrid", description: "Combined semantic + keyword search" },
  clause: { label: "Clause Match", description: "Search within clause text only" },
};

interface SearchBarProps {
  onSearch: (query: string, mode: SearchMode) => void;
  onFilterToggle: () => void;
}

export function SearchBar({ onSearch, onFilterToggle }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchMode, setSearchMode] = useState<SearchMode>("semantic");
  const [showModePicker, setShowModePicker] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
        setShowModePicker(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSearch = useCallback((q?: string) => {
    const searchQuery = q || query;
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setShowDropdown(false);
    onSearch(searchQuery, searchMode);
    setTimeout(() => setIsSearching(false), 800);
  }, [query, searchMode, onSearch]);

  // Keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const modeIcon = {
    semantic: <Brain className="w-3.5 h-3.5" />,
    keyword: <Search className="w-3.5 h-3.5" />,
    vector: <Layers className="w-3.5 h-3.5" />,
    hybrid: <GitMerge className="w-3.5 h-3.5" />,
    ai_assisted: <Sparkles className="w-3.5 h-3.5" />,
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Search Bar */}
      <div className={`flex items-center bg-white dark:bg-navy-800 border-2 rounded-xl transition-all ${
        isFocused ? "border-gold-400 shadow-lg shadow-gold-500/10" : "border-gray-200 dark:border-navy-600 shadow-sm"
      }`}>
        {/* Mode Selector */}
        <div className="relative">
          <button
            onClick={() => setShowModePicker(!showModePicker)}
            className="flex items-center gap-1 pl-3 pr-2 py-2.5 text-[10px] font-medium text-gold-600 dark:text-gold-400 hover:bg-gold-50 dark:hover:bg-gold-900/10 rounded-l-xl transition-colors border-r border-gray-100 dark:border-navy-600"
          >
            {modeIcon[searchMode]}
            <span className="hidden sm:inline">{searchModeLabels[searchMode].label}</span>
            <ChevronDown className="w-2.5 h-2.5" />
          </button>
          <AnimatePresence>
            {showModePicker && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="absolute top-full left-0 mt-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-xl z-20 py-1 w-48"
              >
                {(Object.keys(searchModeLabels) as SearchMode[]).map((key) => {
                  const val = searchModeLabels[key];
                  return (
                    <button
                      key={key}
                      onClick={() => { setSearchMode(key); setShowModePicker(false); }}
                      className={`w-full text-left px-3 py-2 flex items-center gap-2 text-[11px] hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors ${
                        searchMode === key ? "text-gold-600 bg-gold-50/50 dark:bg-gold-900/10" : "text-gray-600 dark:text-gray-300"
                      }`}
                    >
                      {modeIcon[key]}
                      <div>
                        <span className="font-medium">{val.label}</span>
                        <p className="text-[9px] text-gray-400">{val.description}</p>
                      </div>
                    </button>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Input */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => { setQuery(e.target.value); setShowDropdown(true); }}
            onFocus={() => { setIsFocused(true); setShowDropdown(true); }}
            onBlur={() => setIsFocused(false)}
            onKeyDown={e => { if (e.key === "Enter") handleSearch(); }}
            placeholder='Search contracts, clauses, vendors... (e.g., "Find uncapped liability clauses")'
            className="w-full px-3 py-2.5 text-sm bg-transparent text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none"
            aria-label="Search query"
          />
          {/* Clear button */}
          {query && (
            <button
              onClick={() => { setQuery(""); inputRef.current?.focus(); }}
              className="absolute right-1 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 dark:hover:bg-navy-700 rounded transition-colors"
            >
              <X className="w-3.5 h-3.5 text-gray-400" />
            </button>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 pr-2">
          <button
            onClick={onFilterToggle}
            className="p-1.5 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-navy-700 rounded-lg transition-colors"
            title="Filters"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>
          <div className="w-px h-5 bg-gray-200 dark:bg-navy-600" />
          <button
            onClick={() => handleSearch()}
            disabled={isSearching || !query.trim()}
            className="flex items-center gap-1 px-3 py-1.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gray-300 dark:disabled:bg-navy-600 text-white rounded-lg text-xs font-medium transition-colors"
          >
            {isSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">Search</span>
          </button>
        </div>
      </div>

      {/* Dropdown: Suggestions / Recent */}
      <AnimatePresence>
        {showDropdown && isFocused && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-xl shadow-2xl z-30 overflow-hidden"
          >
            {/* Recent Searches — sourced from localStorage in SearchHub */}
            <div className="p-2 border-t border-gray-100 dark:border-navy-700">
              <div className="flex items-center gap-1.5 px-2 py-1">
                <History className="w-3 h-3 text-gray-400" />
                <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Recent Searches</span>
              </div>
              <div className="px-2 py-3 text-center">
                <p className="text-[10px] text-gray-400">Type a search to begin</p>
              </div>
            </div>

            {/* Keyboard shortcut hint */}
            <div className="px-3 py-1.5 bg-gray-50 dark:bg-navy-900 border-t border-gray-100 dark:border-navy-700 text-[9px] text-gray-400 flex items-center justify-between">
              <span>AI-powered semantic search</span>
              <span><kbd className="px-1 py-0.5 bg-gray-200 dark:bg-navy-600 rounded text-[8px]">⌘K</kbd></span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

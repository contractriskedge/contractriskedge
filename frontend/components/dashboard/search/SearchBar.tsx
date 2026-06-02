"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Sparkles, X, Clock, TrendingUp, ChevronDown, Mic,
  Filter, SlidersHorizontal, ArrowRight, History, Bookmark,
  Brain, Layers, GitMerge, Loader2, Bell,
} from "lucide-react";
import type { SearchMode, AiSearchSuggestion, RecentSearch, SavedSearch } from "./types";

const mockAiSuggestions: AiSearchSuggestion[] = [];
const mockRecentSearches: RecentSearch[] = [];
const mockSavedSearches: SavedSearch[] = [];
const searchModeLabels: Record<string, string> = {
  semantic: "AI Semantic",
  keyword: "Keyword",
  hybrid: "Hybrid",
  clause: "Clause Match",
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
                {(Object.entries(searchModeLabels) as [SearchMode, typeof searchModeLabels.semantic][]).map(([key, val]) => (
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
                ))}
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
            {/* AI Suggestions */}
            {query.length > 0 && (
              <div className="p-2">
                <div className="flex items-center gap-1.5 px-2 py-1">
                  <Sparkles className="w-3 h-3 text-purple-500" />
                  <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">AI Suggestions</span>
                </div>
                <div className="space-y-0.5">
                  {mockAiSuggestions.filter(s => s.query.toLowerCase().includes(query.toLowerCase()) || query.length === 0).slice(0, 3).map(s => (
                    <button
                      key={s.id}
                      onClick={() => { setQuery(s.query); handleSearch(s.query); }}
                      className="w-full text-left px-3 py-1.5 flex items-center gap-2 hover:bg-purple-50 dark:hover:bg-purple-900/10 rounded-lg transition-colors group"
                    >
                      <Sparkles className="w-3 h-3 text-purple-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="text-xs text-navy-900 dark:text-white truncate block">{s.query}</span>
                        <span className="text-[9px] text-gray-400">{s.description}</span>
                      </div>
                      <span className="text-[9px] text-purple-500 font-medium opacity-0 group-hover:opacity-100 transition-opacity">{s.confidence}%</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Searches */}
            <div className="p-2 border-t border-gray-100 dark:border-navy-700">
              <div className="flex items-center gap-1.5 px-2 py-1">
                <History className="w-3 h-3 text-gray-400" />
                <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Recent Searches</span>
              </div>
              <div className="space-y-0.5">
                {mockRecentSearches.slice(0, 4).map(rs => (
                  <button
                    key={rs.id}
                    onClick={() => { setQuery(rs.query); handleSearch(rs.query); }}
                    className="w-full text-left px-3 py-1.5 flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors"
                  >
                    <Clock className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    <span className="text-xs text-gray-600 dark:text-gray-300 flex-1 truncate">{rs.query}</span>
                    <span className="text-[9px] text-gray-400">{rs.resultCount} results</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Saved Searches */}
            <div className="p-2 border-t border-gray-100 dark:border-navy-700">
              <div className="flex items-center gap-1.5 px-2 py-1">
                <Bookmark className="w-3 h-3 text-gold-500" />
                <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Saved Searches</span>
              </div>
              <div className="space-y-0.5">
                {mockSavedSearches.slice(0, 3).map(ss => (
                  <button
                    key={ss.id}
                    onClick={() => { setQuery(ss.query); handleSearch(ss.query); }}
                    className="w-full text-left px-3 py-1.5 flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-navy-700 rounded-lg transition-colors"
                  >
                    <Bookmark className="w-3 h-3 text-gold-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-navy-900 dark:text-white truncate block">{ss.name}</span>
                      <span className="text-[9px] text-gray-400">{ss.query}</span>
                    </div>
                    {ss.alertEnabled && <Bell className="w-3 h-3 text-rose-400 flex-shrink-0" />}
                  </button>
                ))}
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

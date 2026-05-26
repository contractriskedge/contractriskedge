"use client";

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText, FileSearch, ClipboardCheck, Building2, Workflow,
  GitMerge, BarChart3, ScrollText, AlertTriangle, ChevronDown,
  ChevronRight, Sparkles, Brain, ArrowUpDown, Clock, Eye,
  Target, Loader2, CheckCircle, XCircle, Info, Search,
} from "lucide-react";
import type { SearchResult, SearchResultType, SearchHighlight } from "./types";

// ── Result Type Icon ─────────────────────────────────────────────────────

const resultTypeIcons: Record<SearchResultType, React.ReactNode> = {
  contract: <FileText className="w-3.5 h-3.5" />,
  clause: <FileSearch className="w-3.5 h-3.5" />,
  obligation: <ClipboardCheck className="w-3.5 h-3.5" />,
  vendor: <Building2 className="w-3.5 h-3.5" />,
  workflow: <Workflow className="w-3.5 h-3.5" />,
  negotiation: <GitMerge className="w-3.5 h-3.5" />,
  benchmark: <BarChart3 className="w-3.5 h-3.5" />,
  audit_event: <ScrollText className="w-3.5 h-3.5" />,
  playbook: <GitMerge className="w-3.5 h-3.5" />,
  redline: <GitMerge className="w-3.5 h-3.5" />,
};

const resultTypeColors: Record<SearchResultType, string> = {
  contract: "text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400",
  clause: "text-amber-600 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-400",
  obligation: "text-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-purple-400",
  vendor: "text-teal-600 bg-teal-50 dark:bg-teal-900/20 dark:text-teal-400",
  workflow: "text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400",
  negotiation: "text-gold-600 bg-gold-50 dark:bg-gold-900/20 dark:text-gold-400",
  benchmark: "text-rose-600 bg-rose-50 dark:bg-rose-900/20 dark:text-rose-400",
  audit_event: "text-slate-600 bg-slate-50 dark:bg-slate-900/20 dark:text-slate-400",
  playbook: "text-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 dark:text-indigo-400",
  redline: "text-orange-600 bg-orange-50 dark:bg-orange-900/20 dark:text-orange-400",
};

// ── Confidence Badge ─────────────────────────────────────────────────────

function ConfidenceBadge({ score }: { score: number }) {
  const color = score >= 95 ? "text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400" :
    score >= 85 ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400" :
    score >= 75 ? "text-amber-600 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-400" :
    "text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400";
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${color}`}>
      {score}%
    </span>
  );
}

// ── Risk Badge ───────────────────────────────────────────────────────────

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    info: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  };
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium flex items-center gap-0.5 ${colors[level] || colors.info}`}>
      {level === "critical" || level === "high" ? <AlertTriangle className="w-2.5 h-2.5" /> : null}
      {level}
    </span>
  );
}

// ── Highlighted Snippet ──────────────────────────────────────────────────

function HighlightedSnippet({ text }: { text: string }) {
  // Handle <mark> tags for highlighting
  const parts = text.split(/(<mark>.*?<\/mark>)/g);
  return (
    <span className="text-[11px] text-gray-600 dark:text-gray-300 leading-relaxed">
      {parts.map((part, i) => {
        if (part.startsWith("<mark>")) {
          const content = part.replace("<mark>", "").replace("</mark>", "");
          return (
            <mark key={i} className="bg-gold-200 dark:bg-gold-900/40 text-navy-900 dark:text-gold-200 px-0.5 rounded">
              {content}
            </mark>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </span>
  );
}

// ── Search Result Card ───────────────────────────────────────────────────

interface SearchResultCardProps {
  result: SearchResult;
  isSelected: boolean;
  onSelect: () => void;
  onPreview: () => void;
}

function SearchResultCard({ result, isSelected, onSelect, onPreview }: SearchResultCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      layout
      className={`border rounded-lg overflow-hidden transition-all cursor-pointer ${
        isSelected
          ? "border-gold-400 shadow-md shadow-gold-500/10 bg-gold-50/30 dark:bg-gold-900/10 dark:border-gold-600"
          : "border-gray-200 dark:border-navy-600 hover:border-gray-300 dark:hover:border-navy-500 hover:shadow-sm bg-white dark:bg-navy-800"
      }`}
      onClick={() => { onSelect(); setExpanded(!expanded); }}
    >
      {/* Header */}
      <div className="px-3 py-2">
        <div className="flex items-start gap-2.5">
          {/* Type Icon */}
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${resultTypeColors[result.type]}`}>
            {resultTypeIcons[result.type]}
          </div>

          <div className="flex-1 min-w-0">
            {/* Title Row */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <h4 className="text-sm font-semibold text-navy-900 dark:text-white truncate">{result.title}</h4>
              <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium capitalize ${resultTypeColors[result.type]}`}>
                {result.type.replace("_", " ")}
              </span>
              <ConfidenceBadge score={result.confidence} />
              <RiskBadge level={result.riskLevel} />
            </div>

            {/* Subtitle */}
            <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">{result.subtitle}</p>

            {/* Snippet with highlights */}
            <div className="mt-1.5">
              <HighlightedSnippet text={result.snippet} />
            </div>

            {/* Semantic Summary (expandable) */}
            <AnimatePresence>
              {expanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  {/* AI Summary */}
                  <div className="mt-2 p-2 bg-purple-50 dark:bg-purple-900/10 border border-purple-100 dark:border-purple-900/30 rounded-lg">
                    <div className="flex items-center gap-1 text-[9px] text-purple-600 dark:text-purple-400 font-medium mb-0.5">
                      <Brain className="w-2.5 h-2.5" />
                      AI Semantic Summary
                    </div>
                    <p className="text-[10px] text-gray-700 dark:text-gray-300 leading-relaxed">{result.semanticSummary}</p>
                  </div>

                  {/* Match Explanation */}
                  <div className="mt-1.5 p-2 bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-lg">
                    <div className="flex items-center gap-1 text-[9px] text-blue-600 dark:text-blue-400 font-medium mb-0.5">
                      <Target className="w-2.5 h-2.5" />
                      Match Explanation
                    </div>
                    <p className="text-[10px] text-gray-700 dark:text-gray-300">{result.matchExplanation}</p>
                  </div>

                  {/* Scores */}
                  <div className="flex items-center gap-2 mt-1.5 text-[9px] text-gray-400">
                    {result.vectorScore !== undefined && <span>Vector: {(result.vectorScore * 100).toFixed(0)}%</span>}
                    {result.keywordScore !== undefined && <span>Keyword: {(result.keywordScore * 100).toFixed(0)}%</span>}
                    {result.hybridScore !== undefined && <span>Hybrid: {(result.hybridScore * 100).toFixed(0)}%</span>}
                  </div>

                  {/* Related Entities */}
                  {result.entities.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {result.entities.map(e => (
                        <span key={e.id} className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400 rounded text-[8px]">
                          {e.label}
                          <span className="text-gray-400">·</span>
                          {e.relationship}
                        </span>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Preview Button */}
          <button
            onClick={e => { e.stopPropagation(); onPreview(); }}
            className="p-1 text-gray-400 hover:text-gold-600 hover:bg-gold-50 dark:hover:bg-gold-900/20 rounded transition-colors flex-shrink-0"
            title="Quick preview"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Meta Row */}
        <div className="flex items-center gap-2 mt-1.5 text-[9px] text-gray-400">
          <Clock className="w-2.5 h-2.5" />
          <span>{new Date(result.lastUpdated).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
          {Object.entries(result.metadata).slice(0, 3).map(([k, v]) => (
            <React.Fragment key={k}>
              <span className="text-gray-300 dark:text-navy-500">·</span>
              <span className="capitalize">{k}: {v}</span>
            </React.Fragment>
          ))}
          <span className="ml-auto flex items-center gap-0.5 text-[8px]">
            {expanded ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
            Details
          </span>
        </div>
      </div>
    </motion.div>
  );
}

// ── Sort Controls ────────────────────────────────────────────────────────

interface SearchResultsPanelProps {
  results: SearchResult[];
  totalResults: number;
  processingTime: number;
  query: string;
  isLoading: boolean;
  onResultSelect: (result: SearchResult) => void;
  onPreview: (result: SearchResult) => void;
  selectedResultId: string | null;
}

export function SearchResultsPanel({
  results, totalResults, processingTime, query, isLoading,
  onResultSelect, onPreview, selectedResultId,
}: SearchResultsPanelProps) {
  const [sortBy, setSortBy] = useState<"relevance" | "date" | "risk" | "name">("relevance");
  const [showSortMenu, setShowSortMenu] = useState(false);

  const sortedResults = useMemo(() => {
    const sorted = [...results];
    switch (sortBy) {
      case "relevance": return sorted.sort((a, b) => b.confidence - a.confidence);
      case "date": return sorted.sort((a, b) => new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime());
      case "risk": {
        const riskOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
        return sorted.sort((a, b) => (riskOrder[a.riskLevel] ?? 5) - (riskOrder[b.riskLevel] ?? 5));
      }
      case "name": return sorted.sort((a, b) => a.title.localeCompare(b.title));
      default: return sorted;
    }
  }, [results, sortBy]);

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-navy-900">
      {/* Results Header */}
      <div className="px-4 py-2 bg-white dark:bg-navy-800 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isLoading ? (
            <Loader2 className="w-4 h-4 text-gold-500 animate-spin" />
          ) : (
            <CheckCircle className="w-4 h-4 text-green-500" />
          )}
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {isLoading ? "Searching..." : (
              <>
                <strong className="text-navy-900 dark:text-white tabular-nums">{totalResults.toLocaleString()}</strong> results
                {query && <> for "<span className="text-navy-900 dark:text-white font-medium">{query}</span>"</>}
                <span className="text-gray-400"> in {processingTime}ms</span>
              </>
            )}
          </span>
        </div>

        {/* Sort */}
        <div className="relative">
          <button
            onClick={() => setShowSortMenu(!showSortMenu)}
            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-navy-700 dark:hover:text-gray-300 transition-colors"
          >
            <ArrowUpDown className="w-3 h-3" />
            Sort: <span className="font-medium text-navy-900 dark:text-white capitalize">{sortBy}</span>
          </button>
          <AnimatePresence>
            {showSortMenu && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="absolute right-0 top-full mt-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-lg z-10 py-1 w-32"
              >
                {(["relevance", "date", "risk", "name"] as const).map(s => (
                  <button
                    key={s}
                    onClick={() => { setSortBy(s); setShowSortMenu(false); }}
                    className={`w-full text-left px-3 py-1.5 text-[10px] capitalize ${
                      sortBy === s ? "text-gold-600 font-semibold bg-gold-50/50" : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Results List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading ? (
          // Loading skeleton
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg p-3 animate-pulse">
                <div className="flex gap-2">
                  <div className="w-7 h-7 bg-gray-200 dark:bg-navy-600 rounded-lg" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-4 bg-gray-200 dark:bg-navy-600 rounded w-3/4" />
                    <div className="h-3 bg-gray-100 dark:bg-navy-700 rounded w-1/2" />
                    <div className="h-8 bg-gray-100 dark:bg-navy-700 rounded w-full" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : sortedResults.length === 0 ? (
          <div className="text-center py-16">
            <Search className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-navy-600" />
            <h3 className="text-sm font-semibold text-navy-900 dark:text-white mb-1">No results found</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Try adjusting your search query or filters</p>
          </div>
        ) : (
          sortedResults.map(result => (
            <SearchResultCard
              key={result.id}
              result={result}
              isSelected={selectedResultId === result.id}
              onSelect={() => onResultSelect(result)}
              onPreview={() => onPreview(result)}
            />
          ))
        )}
      </div>
    </div>
  );
}

"use client";

import React, { useState, useCallback, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, PanelLeft, PanelRight, Sparkles, SlidersHorizontal,
  AlertCircle, RefreshCw,
} from "lucide-react";
import type { SearchMode, SearchFilter, AiDiscoveryInsight, AiSearchSuggestion, SearchResult, SearchResultType, RiskLevel } from "./types";
import { useSearch, usePopularQueries, useTrackSearchClick, useSearchPulse } from "@/services/hooks/useSearch";
import type { SearchPulseResponse } from "@/services/hooks/useSearch";
import type { SearchResultItem } from "@/services/hooks/useSearch";
import { SearchKpiCards } from "./SearchKpiCards";
import type { SearchKpi } from "./types";
import { SearchBar } from "./SearchBar";
import { SearchLeftSidebar } from "./SearchLeftSidebar";
import { SearchResultsPanel } from "./SearchResultsPanel";
import { SearchRightPanel } from "./SearchRightPanel";
import { QuickPreviewDrawer } from "./QuickPreviewDrawer";

// ── Backend → Frontend result converter ──────────────────────────

function toSearchResult(item: SearchResultItem, index: number): SearchResult {
  // Infer a result type from available backend fields
  const typeMap: Record<string, SearchResultType> = {
    contract: "contract",
    clause: "clause",
    obligation: "obligation",
    vendor: "vendor",
    audit_event: "audit_event",
    playbook: "playbook",
    redline: "redline",
  };
  const resultType: SearchResultType =
    (item.clause_type && typeMap[item.clause_type]) ||
    (item.section_heading?.toLowerCase().includes("obligation") ? "obligation" : "clause");

  // Derive a risk level from score (heuristic)
  const riskLevel: RiskLevel =
    item.score >= 0.85 ? "critical" :
    item.score >= 0.70 ? "high" :
    item.score >= 0.50 ? "medium" :
    item.score >= 0.30 ? "low" : "info";

  const title = item.contract_name
    ? `${item.contract_name}${item.section_heading ? ` – ${item.section_heading}` : ""}`
    : item.section_heading ?? `Chunk ${item.chunk_id.slice(0, 8)}`;

  return {
    id: item.chunk_id,
    type: resultType,
    title,
    subtitle: item.contract_name ?? `Page ${item.page_numbers.join(", ")}`,
    snippet: item.snippet,
    semanticSummary: item.snippet.slice(0, 200),
    matchExplanation: `Matched via ${item.strategy} strategy with relevance ${(item.score * 100).toFixed(0)}%`,
    confidence: item.score,
    riskLevel,
    highlights: [],
    entities: [],
    metadata: {
      chunk_id: item.chunk_id,
      contract_id: item.contract_id ?? "",
      strategy: item.strategy,
      page_numbers: item.page_numbers.join(", "),
      token_count: String(item.token_count),
    },
    lastUpdated: "",
    status: "active",
    vectorScore: item.strategy === "vector" || item.strategy === "hybrid" ? item.score : undefined,
    keywordScore: item.strategy === "keyword" || item.strategy === "hybrid" ? item.score : undefined,
    hybridScore: item.strategy === "hybrid" ? item.score : undefined,
  };
}

// ── Default KPI cards (derived from search data) ────────────────

function buildKpis(totalResults: number, avgScore: number, queryCount: number): SearchKpi[] {
  return [
    {
      id: "total-results",
      label: "Total Results",
      value: String(totalResults),
      trend: 0,
      trendDirection: "neutral",
      icon: "FileText",
      color: "blue",
      severity: "info",
      sparklineData: [],
      tooltip: "Total matching chunks found",
    },
    {
      id: "avg-relevance",
      label: "Avg. Relevance",
      value: `${(avgScore * 100).toFixed(0)}%`,
      trend: 0,
      trendDirection: "neutral",
      icon: "Target",
      color: "emerald",
      severity: avgScore >= 0.7 ? "success" : avgScore >= 0.4 ? "warning" : "critical",
      sparklineData: [],
      tooltip: "Average relevance score across results",
    },
    {
      id: "queries-today",
      label: "Queries Today",
      value: String(queryCount),
      trend: 0,
      trendDirection: "neutral",
      icon: "Search",
      color: "purple",
      severity: "info",
      sparklineData: [],
      tooltip: "Popular queries count",
    },
  ];
}

// ── Component ───────────────────────────────────────────────────

export function SearchHub() {
  // Core search state
  const [query, setQuery] = useState("");
  const [searchMode, setSearchMode] = useState<SearchMode>("hybrid");
  const [activeCategory, setActiveCategory] = useState("all");
  const [filters, setFilters] = useState<SearchFilter[]>([]);
  const [debouncedQuery, setDebouncedQuery] = useState<string | null>(null);

  // UI state
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [previewResult, setPreviewResult] = useState<SearchResult | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showLeftSidebar, setShowLeftSidebar] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // ── Hooks ─────────────────────────────────────────────────────

  const searchParams = useMemo(() => {
    if (!debouncedQuery) return null;
    return {
      q: debouncedQuery,
      strategy: (searchMode === "semantic" || searchMode === "ai_assisted" ? "hybrid" : searchMode) as "hybrid" | "vector" | "keyword",
      page: 1,
      page_size: 50,
    };
  }, [debouncedQuery, searchMode]);

  const { data: searchData, isLoading, isError, error, refetch } = useSearch(searchParams);
  const { data: popularData } = usePopularQueries();
  const { data: pulseData } = useSearchPulse();
  const trackClick = useTrackSearchClick();

  // ── Debounce query input ──────────────────────────────────────

  useEffect(() => {
    if (!query.trim()) {
      setDebouncedQuery(null);
      return;
    }
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  // ── Derive frontend results ───────────────────────────────────

  const results: SearchResult[] = useMemo(() => {
    if (!searchData?.results) return [];
    return searchData.results.map((item, i) => toSearchResult(item, i));
  }, [searchData]);

  const totalResults = searchData?.total ?? 0;
  const processingTime = searchData?.latency_ms ?? 0;

  // ── Derive KPIs from real data ────────────────────────────────

  const avgScore = useMemo(() => {
    if (!searchData?.results?.length) return 0;
    return searchData.results.reduce((s, r) => s + r.score, 0) / searchData.results.length;
  }, [searchData]);

  const popularQueryCount = popularData?.queries?.length ?? pulseData?.popular_queries?.length ?? 0;
  // When no search active, show portfolio totals from pulse
  const displayTotalResults = searchData ? totalResults : (pulseData?.total_chunks ?? 0);
  const displayAvgScore = searchData ? avgScore : (pulseData?.avg_risk_score ?? 0);

  const kpis = useMemo(
    () => buildKpis(displayTotalResults, displayAvgScore, popularQueryCount),
    [displayTotalResults, displayAvgScore, popularQueryCount],
  );

  // ── Categories from search data ───────────────────────────────

  const categories = useMemo(() => {
    const typeCounts = new Map<string, number>();
    for (const r of results) {
      typeCounts.set(r.type, (typeCounts.get(r.type) ?? 0) + 1);
    }
    return [
      { id: "all", label: "All Results", icon: "Layers", count: totalResults, description: "All search results" },
      ...Array.from(typeCounts.entries()).map(([type, count]) => ({
        id: type,
        label: type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, " "),
        icon: "FileText",
        count,
        description: `${type.replace(/_/g, " ")} results`,
      })),
    ];
  }, [results, totalResults]);

  // ── Saved searches from popular queries ───────────────────────

  const savedSearches = useMemo(() => {
    if (!popularData?.queries) return [];
    return popularData.queries.map((q, i) => ({
      id: `popular-${i}`,
      name: q.query,
      query: q.query,
      mode: "hybrid" as SearchMode,
      filters: [] as SearchFilter[],
      alertEnabled: false,
      lastRun: "",
      resultCount: q.count,
      frequency: "never" as const,
    }));
  }, [popularData]);

  // ── Filtered results by category ──────────────────────────────

  const filteredResults = useMemo(() => {
    if (activeCategory === "all") return results;
    return results.filter((r) => r.type === activeCategory);
  }, [results, activeCategory]);

  // ── Handlers ──────────────────────────────────────────────────

  const handleSearch = useCallback((q: string, mode: SearchMode) => {
    setQuery(q);
    setSearchMode(mode);
    // The debounce effect will trigger the actual API call
  }, []);

  const handleCategoryChange = useCallback((catId: string) => {
    setActiveCategory(catId);
  }, []);

  const handleFilterAdd = useCallback((filter: SearchFilter) => {
    setFilters((prev) => [...prev, filter]);
  }, []);

  const handleFilterRemove = useCallback((filterId: string) => {
    setFilters((prev) => prev.filter((f) => f.id !== filterId));
  }, []);

  const handleClearFilters = useCallback(() => {
    setFilters([]);
  }, []);

  const handleSavedSearchSelect = useCallback((saved: { query: string; mode: SearchMode }) => {
    handleSearch(saved.query, saved.mode);
  }, [handleSearch]);

  const handleResultSelect = useCallback((result: SearchResult) => {
    setSelectedResultId((prev) => (prev === result.id ? null : result.id));
    // Track the click
    trackClick.mutate({
      query: debouncedQuery ?? "",
      result_id: result.id,
      position: results.findIndex((r) => r.id === result.id) + 1,
    });
  }, [debouncedQuery, results, trackClick]);

  const handlePreview = useCallback((result: SearchResult) => {
    setPreviewResult(result);
    setShowPreview(true);
  }, []);

  const handleInsightClick = useCallback((insight: AiDiscoveryInsight) => {
    if (insight.suggestedQuery) {
      handleSearch(insight.suggestedQuery, "ai_assisted");
    }
  }, [handleSearch]);

  const handleSuggestionClick = useCallback((suggestion: AiSearchSuggestion) => {
    handleSearch(suggestion.query, "ai_assisted");
  }, [handleSearch]);

  const handleKpiClick = useCallback((kpiId: string) => {
    // For real KPIs, clicking a KPI could navigate or run a specific search
    if (kpiId === "total-results" && query) {
      refetch();
    }
  }, [query, refetch]);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  // ── Error state ───────────────────────────────────────────────

  if (isError && debouncedQuery) {
    return (
      <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
        {/* KPI Row */}
        <div className="px-4 pt-3 pb-2">
          <SearchKpiCards metrics={kpis} onKpiClick={handleKpiClick} />
        </div>

        {/* Search Bar */}
        <div className="px-4 pb-3">
          <SearchBar onSearch={handleSearch} onFilterToggle={() => setShowFilterPanel(!showFilterPanel)} />
        </div>

        {/* Error Message */}
        <div className="flex-1 flex items-center justify-center px-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center text-center max-w-md"
          >
            <div className="w-14 h-14 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-4">
              <AlertCircle className="w-7 h-7 text-red-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
              Search Failed
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              {(error as Error)?.message ?? "An unexpected error occurred while searching. Please try again."}
            </p>
            <button
              onClick={handleRetry}
              className="inline-flex items-center gap-2 px-4 py-2 bg-navy-600 hover:bg-navy-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retry Search
            </button>
          </motion.div>
        </div>

        <QuickPreviewDrawer
          result={previewResult}
          isOpen={showPreview}
          onClose={() => setShowPreview(false)}
        />
      </div>
    );
  }

  // ── Empty state (no query yet) ────────────────────────────────

  const showEmptyState = !debouncedQuery && !isLoading;

  // ── Main render ───────────────────────────────────────────────

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-navy-900">
      {/* KPI Row */}
      <div className="px-4 pt-3 pb-2">
        <SearchKpiCards metrics={kpis} onKpiClick={handleKpiClick} />
      </div>

      {/* Search Bar */}
      <div className="px-4 pb-3">
        <SearchBar onSearch={handleSearch} onFilterToggle={() => setShowFilterPanel(!showFilterPanel)} />
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex min-h-0">
        {/* Left Sidebar Toggle */}
        {!showLeftSidebar && (
          <button
            onClick={() => setShowLeftSidebar(true)}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 transition-colors"
          >
            <PanelLeft className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Left Sidebar */}
        <AnimatePresence>
          {showLeftSidebar && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 256, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden flex-shrink-0"
            >
              <SearchLeftSidebar
                categories={categories}
                activeCategory={activeCategory}
                onCategoryChange={handleCategoryChange}
                filters={filters}
                onFilterAdd={handleFilterAdd}
                onFilterRemove={handleFilterRemove}
                onClearFilters={handleClearFilters}
                savedSearches={savedSearches}
                onSavedSearchSelect={handleSavedSearchSelect}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Center: Results */}
        {showEmptyState ? (
          <div className="flex-1 flex items-center justify-center px-4">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center text-center max-w-sm"
            >
              <div className="w-16 h-16 rounded-full bg-navy-100 dark:bg-navy-800 flex items-center justify-center mb-4">
                <Search className="w-8 h-8 text-navy-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                Search Contracts &amp; Clauses
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Enter a query above to search across your contract repository. Use filters and categories to narrow results.
              </p>
            </motion.div>
          </div>
        ) : (
          <SearchResultsPanel
            results={filteredResults}
            totalResults={totalResults}
            processingTime={processingTime}
            query={debouncedQuery ?? ""}
            isLoading={isLoading}
            onResultSelect={handleResultSelect}
            onPreview={handlePreview}
            selectedResultId={selectedResultId}
          />
        )}

        {/* Right Panel Toggle */}
        {!showRightPanel && (
          <button
            onClick={() => setShowRightPanel(true)}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 transition-colors"
          >
            <PanelRight className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Right Panel */}
        <AnimatePresence>
          {showRightPanel && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden flex-shrink-0"
            >
              <SearchRightPanel
                insights={pulseData?.insights ?? []}
                suggestions={pulseData?.suggestions ?? []}
                analytics={pulseData?.popular_queries ?? []}
                onInsightClick={handleInsightClick}
                onSuggestionClick={handleSuggestionClick}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Quick Preview Drawer */}
      <QuickPreviewDrawer
        result={previewResult}
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
      />
    </div>
  );
}

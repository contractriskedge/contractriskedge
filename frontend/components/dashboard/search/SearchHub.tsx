"use client";

import React, { useState, useCallback, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, PanelLeft, PanelRight, Sparkles, SlidersHorizontal,
  AlertCircle, RefreshCw, Clock, TrendingUp, Shield,
  AlertTriangle, Calendar,
  Globe, Scale, Hash, BarChart3, Layers, Settings,
} from "lucide-react";
import type { SearchMode, SearchFilter, AiDiscoveryInsight, AiSearchSuggestion, SearchResult, SearchResultType, RiskLevel, SearchAnalytics } from "./types";
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
import {
  WidgetContainer,
  WidgetPreferencesModal,
  useWidgetPreferences,
  type WidgetDefinition,
} from "@/components/shared/WidgetManager";

// ── Backend → Frontend result converter ──────────────────────────

function toSearchResult(item: SearchResultItem, index: number): SearchResult {
  // Infer a result type from available backend fields
  const entityType = item.entity_type || "chunk";
  const typeMap: Record<string, SearchResultType> = {
    chunk: "clause",
    finding: "clause",
    obligation: "obligation",
    redline: "redline",
    contract: "contract",
    vendor: "vendor",
    audit_event: "audit_event",
    playbook: "playbook",
  };
  const resultType: SearchResultType = typeMap[entityType] || "clause";

  // Derive a risk level from score (heuristic)
  const riskLevel: RiskLevel =
    item.score >= 8.5 ? "critical" :
    item.score >= 7.0 ? "high" :
    item.score >= 5.0 ? "medium" :
    item.score >= 3.0 ? "low" : "info";

  let title = item.contract_name
    ? `${item.contract_name}${item.section_heading ? ` – ${item.section_heading}` : ""}`
    : item.section_heading ?? `Result ${index + 1}`;

  // Entity-specific title formatting
  if (entityType === "obligation") {
    title = item.snippet?.split(":")[0] || item.contract_name || "Obligation";
  } else if (entityType === "finding") {
    title = item.snippet?.split(":")[0] || "Finding";
  }

  const subtitle = entityType === "obligation"
    ? `${item.contract_name || ""}${item.status ? ` · ${item.status}` : ""}`
    : entityType === "finding"
    ? `${item.contract_name || ""}${item.clause_type ? ` · ${item.clause_type}` : ""}`
    : item.contract_name ?? `Page ${item.page_numbers.join(", ")}`;

  return {
    id: item.chunk_id,
    type: resultType,
    title,
    subtitle,
    snippet: item.snippet,
    semanticSummary: item.snippet.slice(0, 200),
    matchExplanation: `Matched via ${item.strategy} strategy with relevance ${(item.score * 10).toFixed(0)}%`,
    confidence: item.score / 10,
    riskLevel,
    highlights: [],
    entities: [],
    metadata: {
      chunk_id: item.chunk_id,
      entity_id: item.entity_id ?? "",
      entity_type: entityType,
      review_id: item.review_id ?? item.contract_id ?? "",
      contract_id: item.review_id ?? item.contract_id ?? "",
      upload_id: item.upload_id ?? "",
      contract_number: item.contract_number ?? "",
      strategy: item.strategy,
      page_numbers: item.page_numbers.join(", "),
      token_count: String(item.token_count),
      status: item.status ?? "",
      owner: item.owner ?? "",
      due_date: item.due_date ?? "",
    },
    lastUpdated: item.due_date ?? "",
    status: item.status ?? "active",
    vectorScore: item.strategy === "vector" || item.strategy === "hybrid" ? item.score : undefined,
    keywordScore: item.strategy === "keyword" || item.strategy === "hybrid" ? item.score : undefined,
    hybridScore: item.strategy === "hybrid" ? item.score : undefined,
  };
}

function getSearchResultHref(result: SearchResult): string | null {
  const meta = result.metadata ?? {};
  const entityType = String(meta.entity_type || result.type);
  const reviewId = String(meta.review_id || meta.contract_id || "");
  const entityId = String(meta.entity_id || "");

  if (entityType === "obligation" && entityId) {
    return `/obligations/${entityId}`;
  }
  if (entityType === "finding" && reviewId) {
    const params = new URLSearchParams({ reviewId });
    if (entityId) params.set("findingId", entityId);
    return `/reviews/ai-workspace?${params.toString()}`;
  }
  if (reviewId) {
    return `/contracts/${reviewId}`;
  }
  return null;
}

function stripSyntheticId(id: string): string {
  return id.replace(/^(ilike-|finding-|obligation-)/, "");
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
      label: "Search Ranking Strength",
      value: (avgScore * 1000).toFixed(1),
      trend: 0,
      trendDirection: "neutral",
      icon: "Target",
      color: "emerald",
      severity: avgScore >= 0.7 ? "success" : avgScore >= 0.4 ? "warning" : "critical",
      sparklineData: [],
      tooltip: "Measures how consistently results rank highly across semantic and keyword search. Higher values indicate stronger agreement between ranking methods. Scale: 0-20+.",
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
  const router = useRouter();

  // Core search state — read initial query from URL ?q= param
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
  const [rightPanelMode, setRightPanelMode] = useState<"open" | "minimized">("open");
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // ── Hooks ─────────────────────────────────────────────────────

  const searchParams = useMemo(() => {
    if (!debouncedQuery) return null;
    return {
      q: debouncedQuery,
      strategy: (searchMode === "semantic" || searchMode === "ai_assisted" ? "hybrid" : searchMode) as "hybrid" | "vector" | "keyword",
      entity_types: "chunk,finding,obligation",
      page: 1,
      page_size: 50,
    };
  }, [debouncedQuery, searchMode]);

  const { data: searchData, isLoading, isError, error, refetch } = useSearch(searchParams);
  const { data: popularData } = usePopularQueries();
  const { data: pulseData } = useSearchPulse();
  const trackClick = useTrackSearchClick();

  // ── Read ?q= from URL on mount ───────────────────────────────

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    if (q) {
      setQuery(q);
    }
  }, []);

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

  // Queries today: use the actual count from the pulse endpoint (search_queries table, last 24h)
  const queriesToday = pulseData?.queries_today ?? 0;
  // When no search active, show portfolio totals from pulse
  const displayTotalResults = searchData ? totalResults : (pulseData?.total_chunks ?? 0);
  const displayAvgScore = searchData ? avgScore : (pulseData?.avg_risk_score ?? 0);

  const kpis = useMemo(
    () => buildKpis(displayTotalResults, displayAvgScore, queriesToday),
    [displayTotalResults, displayAvgScore, queriesToday],
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
    const position = results.findIndex((r) => r.id === result.id);
    const entityType = String(result.metadata?.entity_type || result.type);
    const entityId = stripSyntheticId(String(result.metadata?.entity_id || result.id));

    trackClick.mutate({
      query: debouncedQuery ?? "",
      result_position: Math.max(position, 0),
      entity_type: entityType,
      entity_id: entityId,
      chunk_id: entityType === "chunk" ? stripSyntheticId(String(result.metadata?.chunk_id || result.id)) : undefined,
      score: result.confidence,
    });

    const href = getSearchResultHref(result);
    if (href) {
      router.push(href);
    }
  }, [debouncedQuery, results, trackClick, router]);

  const handlePreview = useCallback((result: SearchResult) => {
    const href = getSearchResultHref(result);
    if (href) {
      router.push(href);
    }
  }, [router]);

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

  // ── Recent searches from localStorage ──────────────────────────

  const RECENT_SEARCHES_KEY = "contractriskedge_recent_searches";

  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem(RECENT_SEARCHES_KEY);
      return stored ? (JSON.parse(stored) as string[]) : [];
    } catch {
      return [];
    }
  });

  // Persist a search to localStorage whenever a debounced query fires
  useEffect(() => {
    if (!debouncedQuery) return;
    setRecentSearches((prev) => {
      const updated = [debouncedQuery, ...prev.filter((s) => s !== debouncedQuery)].slice(0, 5);
      try {
        localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
      } catch { /* ignore */ }
      return updated;
    });
  }, [debouncedQuery]);

  // ── Suggested search cards from backend pulse data ────────────

  const suggestedSearches = useMemo(() => {
    // Use real backend suggestions if available
    if (pulseData?.suggestions && pulseData.suggestions.length > 0) {
      const iconMap = [
        { icon: Shield, color: "text-purple-500", bg: "bg-purple-50 dark:bg-purple-900/20" },
        { icon: AlertTriangle, color: "text-red-500", bg: "bg-red-50 dark:bg-red-900/20" },
        { icon: Globe, color: "text-green-500", bg: "bg-green-50 dark:bg-green-900/20" },
        { icon: Scale, color: "text-cyan-500", bg: "bg-cyan-50 dark:bg-cyan-900/20" },
        { icon: AlertTriangle, color: "text-amber-500", bg: "bg-amber-50 dark:bg-amber-900/20" },
        { icon: Shield, color: "text-blue-500", bg: "bg-blue-50 dark:bg-blue-900/20" },
      ];
      return pulseData.suggestions.map((s, i) => ({
        label: s.description.split(":")[0] || s.query,
        description: s.description,
        query: s.query,
        count: s.result_count,
        severity: s.severity,
        icon: iconMap[i % iconMap.length].icon,
        color: iconMap[i % iconMap.length].color,
        bg: iconMap[i % iconMap.length].bg,
      }));
    }
    // Fallback: hardcoded suggestions when no backend data
    return [
      {
        label: "High risk contracts",
        description: "Contracts with elevated risk scores",
        query: "high risk",
        count: pulseData ? Math.round(pulseData.total_contracts * 0.08) : null,
        severity: "critical",
        icon: AlertTriangle,
        color: "text-red-500",
        bg: "bg-red-50 dark:bg-red-900/20",
      },
      {
        label: "Missing indemnification",
        description: "Contracts lacking indemnity clauses",
        query: "indemnification",
        count: pulseData ? Math.round(pulseData.total_findings * 0.15) : null,
        severity: "critical",
        icon: Shield,
        color: "text-purple-500",
        bg: "bg-purple-50 dark:bg-purple-900/20",
      },
      {
        label: "GDPR compliance issues",
        description: "Data protection compliance gaps",
        query: "GDPR",
        count: pulseData ? Math.round(pulseData.total_findings * 0.08) : null,
        severity: "warning",
        icon: Globe,
        color: "text-green-500",
        bg: "bg-green-50 dark:bg-green-900/20",
      },
      {
        label: "Limitation of liability",
        description: "Liability cap clauses",
        query: "liability cap",
        count: pulseData ? Math.round(pulseData.total_findings * 0.12) : null,
        severity: "warning",
        icon: Scale,
        color: "text-cyan-500",
        bg: "bg-cyan-50 dark:bg-cyan-900/20",
      },
    ];
  }, [pulseData]);

  // ── Popular queries from pulse / popular hooks ─────────────────

  const popularQueries = useMemo(() => {
    const fromPulse = pulseData?.popular_queries;
    const fromPopular = popularData?.queries;
    if (fromPulse && fromPulse.length > 0) return fromPulse;
    if (fromPopular && fromPopular.length > 0)
      return fromPopular.map((q) => ({ query: q.query, frequency: q.count }));
    return null;
  }, [pulseData, popularData]);

  // ── Empty state (no query yet) ────────────────────────────────

  const showEmptyState = !debouncedQuery && !isLoading;

  // ── Widget personalization ────────────────────────────────────

  const widgetDefinitions: WidgetDefinition[] = useMemo(() => [
    { id: "suggested-searches", label: "Suggested Searches", defaultVisible: true, description: "Quick-access search suggestions" },
    { id: "search-trends", label: "Search Trends", defaultVisible: true, description: "Popular and trending queries" },
    { id: "discovery-insights", label: "Discovery Insights", defaultVisible: true, description: "Portfolio-level intelligence" },
    { id: "recent-searches", label: "Recent Searches", defaultVisible: true, description: "Your recent search history" },
  ], []);

  const {
    preferences: widgetPrefs,
    visibleWidgets,
    updatePreference,
    resetDefaults,
  } = useWidgetPreferences("search-discovery", widgetDefinitions);

  const [showWidgetPrefs, setShowWidgetPrefs] = useState(false);

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

        {/* Center: Results / Landing */}
        {showEmptyState ? (
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {/* Header with Customize button */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 flex items-center justify-between"
            >
              <p className="text-base text-gray-500 dark:text-gray-400">
                Start with a search or choose an intelligence insight below
              </p>
              <button
                onClick={() => setShowWidgetPrefs(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium rounded-lg bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
              >
                <Settings className="w-3 h-3" />
                Customize
              </button>
            </motion.div>

            <div className="max-w-5xl mx-auto space-y-6">
              {/* ── 1. Suggested Searches ─────────────────────────── */}
              {widgetPrefs["suggested-searches"] !== false && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 }}
                >
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    Suggested Searches
                  </h3>
                  <div className="grid grid-cols-3 gap-3">
                    {suggestedSearches.map((s) => {
                      const Icon = s.icon;
                      return (
                        <button
                          key={s.query}
                          onClick={() => handleSearch(s.query, "hybrid")}
                          className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4 text-left hover:shadow-md hover:border-navy-300 dark:hover:border-navy-600 transition-all group relative"
                        >
                          {s.count !== null && (
                            <span className={`absolute top-2 right-2 text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${
                              s.severity === "critical" ? "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400" :
                              s.severity === "warning" ? "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400" :
                              "bg-navy-100 dark:bg-navy-700 text-navy-600 dark:text-navy-300"
                            }`}>
                              {s.count}
                            </span>
                          )}
                          <div className={`w-9 h-9 rounded-lg ${s.bg} flex items-center justify-center mb-2.5 group-hover:scale-110 transition-transform`}>
                            <Icon className={`w-4.5 h-4.5 ${s.color}`} />
                          </div>
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{s.label}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{s.description}</p>
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              )}

              {/* ── 2. Search Trends + 3. Discovery Insights + 4. Recent Searches ── */}
              <div className="grid grid-cols-3 gap-4">
                {/* Search Trends Panel */}
                {widgetPrefs["search-trends"] !== false && (
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4"
                  >
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-blue-500" />
                      Search Trends
                    </h3>
                    {popularQueries && popularQueries.length >= 5 ? (
                      <ul className="space-y-2">
                        {popularQueries.slice(0, 10).map((pq, i) => (
                          <li key={i}>
                            <button
                              onClick={() => handleSearch(pq.query, "hybrid")}
                              className="w-full flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors text-left group"
                            >
                              <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-navy-600 dark:group-hover:text-white truncate">
                                {pq.query}
                              </span>
                              <span className="text-xs font-medium text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-navy-700 px-2 py-0.5 rounded-full flex-shrink-0 ml-2">
                                {"frequency" in pq ? (pq as { query: string; frequency: number }).frequency : (pq as { query: string; count: number }).count}
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="flex flex-col items-center py-6 text-center">
                        <BarChart3 className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
                        <p className="text-xs text-gray-400 dark:text-gray-500">No trend data available yet</p>
                        <p className="text-[10px] text-gray-300 dark:text-gray-600 mt-0.5">At least 5 searches required for trends</p>
                      </div>
                    )}
                  </motion.div>
                )}

                {/* Discovery Insights Panel */}
                {widgetPrefs["discovery-insights"] !== false && (
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                    className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4"
                  >
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                      <Layers className="w-4 h-4 text-emerald-500" />
                      Discovery Insights
                    </h3>
                    {pulseData ? (
                      <div className="space-y-2">
                        {pulseData.insights.map((insight, i) => (
                          <button
                            key={i}
                            onClick={() => handleSearch(insight.suggested_query ?? insight.title, "hybrid")}
                            className={`w-full flex items-center justify-between py-1.5 px-2 rounded-lg transition-colors text-left group ${
                              insight.severity === "critical" ? "bg-red-50 dark:bg-red-900/10 hover:bg-red-100 dark:hover:bg-red-900/20" :
                              insight.severity === "warning" ? "bg-amber-50 dark:bg-amber-900/10 hover:bg-amber-100 dark:hover:bg-amber-900/20" :
                              "bg-blue-50 dark:bg-blue-900/10 hover:bg-blue-100 dark:hover:bg-blue-900/20"
                            }`}
                          >
                            <div className="min-w-0 flex-1">
                              <span className={`text-xs font-medium truncate block ${
                                insight.severity === "critical" ? "text-red-700 dark:text-red-400" :
                                insight.severity === "warning" ? "text-amber-700 dark:text-amber-400" :
                                "text-blue-700 dark:text-blue-400"
                              }`}>{insight.title}</span>
                              <span className="text-[9px] text-gray-500 dark:text-gray-400 truncate block">{insight.description}</span>
                            </div>
                            <span className={`text-xs font-semibold flex-shrink-0 ml-2 ${
                              insight.severity === "critical" ? "text-red-600" :
                              insight.severity === "warning" ? "text-amber-600" :
                              "text-blue-600"
                            }`}>{insight.finding_count}</span>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center py-6 text-center">
                        <Hash className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
                        <p className="text-xs text-gray-400 dark:text-gray-500">No portfolio data loaded</p>
                        <p className="text-[10px] text-gray-300 dark:text-gray-600 mt-0.5">Insights appear once the index is built</p>
                      </div>
                    )}
                  </motion.div>
                )}

                {/* Recent Searches Panel */}
                {widgetPrefs["recent-searches"] !== false && (
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4"
                  >
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                      <Clock className="w-4 h-4 text-gray-500" />
                      Recent Searches
                    </h3>
                    {recentSearches.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {recentSearches.map((sq) => (
                          <button
                            key={sq}
                            onClick={() => handleSearch(sq, "hybrid")}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-navy-700 hover:bg-navy-100 dark:hover:bg-navy-600 text-gray-700 dark:text-gray-300 rounded-full text-xs font-medium transition-colors"
                          >
                            <Clock className="w-3 h-3 text-gray-400" />
                            {sq}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center py-6 text-center">
                        <Search className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
                        <p className="text-xs text-gray-400 dark:text-gray-500">No recent searches</p>
                        <p className="text-[10px] text-gray-300 dark:text-gray-600 mt-0.5">Your recent queries will appear here</p>
                      </div>
                    )}
                  </motion.div>
                )}
              </div>
            </div>

            {/* Widget Preferences Modal */}
            <WidgetPreferencesModal
              isOpen={showWidgetPrefs}
              onClose={() => setShowWidgetPrefs(false)}
              title="Search & Discovery"
              widgets={widgetDefinitions}
              preferences={widgetPrefs}
              onToggle={updatePreference}
              onReset={resetDefaults}
            />
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

        {/* Right Panel — Minimized dock */}
        {rightPanelMode === "minimized" && (
          <button
            onClick={() => setRightPanelMode("open")}
            className="flex flex-col items-center gap-1 px-2 py-3 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 transition-colors cursor-pointer"
            title="Open AI Copilot"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
            </svg>
            <span className="text-[7px] font-semibold uppercase tracking-wider whitespace-nowrap writing-mode-vertical">AI Copilot</span>
          </button>
        )}

        {/* Right Panel — Open / Expanded */}
        {!showRightPanel && rightPanelMode !== "minimized" && (
          <button
            onClick={() => { setShowRightPanel(true); setRightPanelMode("open"); }}
            className="flex items-center gap-1 px-1.5 py-1 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 text-gray-400 hover:text-navy-600 dark:hover:text-gray-300 transition-colors"
          >
            <PanelRight className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Right Panel */}
        <AnimatePresence>
          {showRightPanel && rightPanelMode === "open" && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 340, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden flex-shrink-0"
            >
              <SearchRightPanel
                insights={(pulseData?.insights ?? []).map((insight, i) => ({
                  id: `insight-${i}`,
                  type: (insight.type === "pattern" || insight.type === "relationship" || insight.type === "anomaly" || insight.type === "recommendation" || insight.type === "risk" || insight.type === "compliance" ? insight.type : "pattern") as AiDiscoveryInsight["type"],
                  title: insight.title,
                  description: insight.description,
                  severity: (insight.severity === "critical" || insight.severity === "warning" || insight.severity === "info" || insight.severity === "success" ? insight.severity : "info") as AiDiscoveryInsight["severity"],
                  confidence: insight.confidence,
                  impact: (insight.impact === "high" || insight.impact === "medium" || insight.impact === "low" ? insight.impact : "medium") as AiDiscoveryInsight["impact"],
                  entities: insight.entities,
                  suggestedQuery: insight.suggested_query ?? undefined,
                }))}
                suggestions={(pulseData?.suggestions ?? []).map((s, i) => ({
                  id: `suggestion-${i}`,
                  query: s.query,
                  description: s.description,
                  type: "exploration" as const,
                  confidence: 85,
                  reason: `${s.result_count} matching contracts found`,
                }))}
                analytics={pulseData ? {
                  totalSearches: pulseData.queries_today,
                  avgLatency: -1,
                  semanticAccuracy: -1,
                  zeroResultRate: -1,
                  clickThroughRate: -1,
                  popularSearches: (pulseData.popular_queries ?? []).map(q => ({
                    query: q.query,
                    count: q.frequency,
                    trend: 0,
                  })),
                  failedSearches: [],
                  searchTrends: [],
                  latencyDistribution: [],
                  categoryDistribution: [],
                  aiRetrievalQuality: [],
                } as SearchAnalytics : null}
                onInsightClick={handleInsightClick}
                onSuggestionClick={handleSuggestionClick}
                onMinimize={() => setRightPanelMode("minimized")}
                onClose={() => { setShowRightPanel(false); setRightPanelMode("open"); }}
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

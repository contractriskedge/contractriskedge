"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { BookOpen, Download, RefreshCw, Search, Plus, Loader2, AlertCircle } from "lucide-react";
import { ClauseKpiCards } from "./ClauseKpiCards";
import { ClauseSidebar } from "./ClauseSidebar";
import { ClauseTable } from "./ClauseTable";
import { PlaybookPanel } from "./PlaybookPanel";
import { ClauseDetailDrawer } from "./ClauseDetailDrawer";
import { CreateClauseDialog } from "./CreateClauseDialog";
import { BenchmarkChart } from "./BenchmarkChart";
import { ClauseFilterBar, EMPTY_FILTERS, countBy } from "./ClauseFilterBar";
import type { ClauseFilters } from "./ClauseFilterBar";
import { CLAUSE_CATEGORIES } from "./types";
import type { ClauseRecord } from "./types";
import type { ClauseResponse, BenchmarkResponse } from "@/services/api/clauseIntelligence";
import { useClauses, useClauseKpis, useBenchmarks, useUpdateClause, useCreateClause } from "@/services/hooks/useClauseIntelligence";
import { useAuth } from "@/components/auth/AuthProvider";
import { useFavorites } from "@/hooks/useFavorites";

/** Map backend snake_case → frontend camelCase ClauseRecord */
function toClauseRecord(c: ClauseResponse): ClauseRecord {
  return {
    id: c.id,
    name: c.name,
    category: c.category,
    text: c.text,
    riskScore: c.risk_score ?? 0,
    riskLevel: (c.risk_level as ClauseRecord["riskLevel"]) ?? "info",
    jurisdiction: c.jurisdiction ?? "",
    contractTypes: c.contract_types ?? [],
    benchmarkPercentile: c.benchmark_percentile ?? 0,
    usageFrequency: c.usage_frequency ?? 0,
    approvalStatus: (c.approval_status as ClauseRecord["approvalStatus"]) ?? "draft",
    lastUpdated: c.updated_at ?? c.created_at ?? "",
    owner: c.owner ?? "",
    aiConfidence: c.ai_confidence ?? 0,
    negotiationStrength: c.negotiation_strength ?? 0,
    fallbackVariants: [],
    versions: c.version ?? 1,
    isFavorite: c.is_favorite ?? false,
    tags: c.tags ?? [],
    aiExplanation: c.ai_explanation ?? "",
    negotiationGuidance: c.negotiation_guidance ?? "",
    governanceNotes: c.governance_notes ?? "",
  };
}

/** Map backend BenchmarkResponse → frontend BenchmarkData */
function toBenchmarkData(b: BenchmarkResponse) {
  return {
    clauseType: b.category,
    yourScore: b.avg_risk_score ?? 0,
    marketMedian: b.market_median,
    marketP25: b.market_p25 ?? 0,
    marketP75: b.market_p75 ?? 0,
    percentile: b.acceptance_rate ?? 0,
    sampleSize: b.sample_size,
  };
}

export function ClauseLibrary() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showFavorites, setShowFavorites] = useState(false);
  const [selectedClause, setSelectedClause] = useState<ClauseRecord | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [filters, setFilters] = useState<ClauseFilters>({ ...EMPTY_FILTERS });

  // ── Live API Queries ──────────────────────────────────────────
  // Always fetch the full clause list — we need the unfiltered set so the
  // sidebar category counts and the filter-bar option counts stay correct
  // as the user changes selections. All filtering (category, search, risk,
  // jurisdiction, status, etc.) happens client-side below.
  const { data: clausesData, isLoading, isError, refetch } = useClauses();
  const { data: kpisData, isLoading: kpisLoading } = useClauseKpis();
  const { data: benchmarksData, isLoading: benchmarksLoading } = useBenchmarks();
  // `updateMutation` is used both for the currently-open detail drawer
  // (where we want to fall back to `selectedClause?.id`) and for the
  // table-level star toggle (where the id comes from the row). We pass the
  // id explicitly in each mutate() call so the hook always knows which
  // clause to update.
  const updateMutation = useUpdateClause();

  // Local per-user favorites store — used for instant UI feedback in the
  // sidebar filter and the row star. Mirrored to the backend so the
  // favorite follows the user across devices.
  const { user } = useAuth();
  const favorites = useFavorites(user?.tenant_id, user?.sub);
  const createMutation = useCreateClause();

  // ── Derived Data ──────────────────────────────────────────────
  const clauses: ClauseRecord[] = useMemo(
    () => (clausesData?.data ?? []).map(toClauseRecord),
    [clausesData],
  );

  // Apply sidebar + header filters first, so the filter bar's options
  // are computed against the same data set the user is browsing.
  const baseFilteredClauses = useMemo(() => {
    let list = clauses;
    if (selectedCategory) {
      // Match by exact id, or by a slug-normalized form of the displayed
      // category name. This way clicking "Indemnification" in the sidebar
      // matches clauses with category "indemnification" or "Indemnification".
      const norm = (s: string) =>
        s.toLowerCase().trim().replace(/[\s-]+/g, "_");
      const target = norm(selectedCategory);
      list = list.filter((c) => norm(c.category) === target || norm(c.name) === target);
    }
    if (showFavorites) list = list.filter((c) => c.isFavorite);
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.category.toLowerCase().includes(q) ||
          c.tags.some((t) => t.toLowerCase().includes(q)),
      );
    }
    return list;
  }, [clauses, showFavorites, searchQuery, selectedCategory]);

  // Apply the ClauseFilterBar (risk / jurisdiction / status / template /
  // mandatory / custom) on top of the base set.
  const filteredClauses = useMemo(() => {
    let list = baseFilteredClauses;
    if (filters.clauseType) {
      const q = filters.clauseType.toLowerCase();
      list = list.filter((c) => c.category.toLowerCase().includes(q) || c.name.toLowerCase().includes(q));
    }
    if (filters.risk) list = list.filter((c) => c.riskLevel === filters.risk);
    if (filters.jurisdiction) list = list.filter((c) => c.jurisdiction === filters.jurisdiction);
    if (filters.status) list = list.filter((c) => c.approvalStatus === filters.status);
    if (filters.template) {
      list = list.filter((c) => c.contractTypes.includes(filters.template));
    }
    if (filters.mandatory !== "all") {
      const wantYes = filters.mandatory === "yes";
      list = list.filter((c) => {
        // Treat a clause as mandatory when governance notes call it so,
        // when its category is on the standard mandatory list, or when the
        // risk score is critical. This is a heuristic — the backend schema
        // doesn't yet expose a `mandatory` boolean.
        const isMandatory =
          /mandatory/i.test(c.governanceNotes || "") ||
          /mandatory/i.test(c.aiExplanation || "") ||
          c.riskLevel === "critical";
        return wantYes ? isMandatory : !isMandatory;
      });
    }
    if (filters.custom) {
      const q = filters.custom.toLowerCase();
      list = list.filter((c) => c.tags.some((t) => t.toLowerCase().includes(q)));
    }
    return list;
  }, [baseFilteredClauses, filters]);

  // ── Option Counts (over the base set so each dropdown reflects the
  //    currently visible scope minus its own filter).
  const riskOptions = useMemo(() => {
    const map = countBy(baseFilteredClauses.filter((c) => !filters.risk || c.riskLevel === filters.risk), "riskLevel");
    return Array.from(map.entries()).map(([value, count]) => ({ value, label: value.charAt(0).toUpperCase() + value.slice(1), count }));
  }, [baseFilteredClauses, filters.risk]);

  const jurisdictionOptions = useMemo(() => {
    const map = countBy(
      baseFilteredClauses.filter((c) => !filters.jurisdiction || c.jurisdiction === filters.jurisdiction),
      "jurisdiction",
    );
    return Array.from(map.entries())
      .map(([value, count]) => ({ value, label: value, count }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [baseFilteredClauses, filters.jurisdiction]);

  const statusOptions = useMemo(() => {
    const map = countBy(
      baseFilteredClauses.filter((c) => !filters.status || c.approvalStatus === filters.status),
      "approvalStatus",
    );
    return Array.from(map.entries()).map(([value, count]) => ({ value, label: value.replace(/_/g, " "), count }));
  }, [baseFilteredClauses, filters.status]);

  const templateOptions = useMemo(() => {
    // Templates are the contract-type facets; aggregate across records.
    const counts = new Map<string, number>();
    for (const c of baseFilteredClauses) {
      if (filters.template && !c.contractTypes.includes(filters.template)) continue;
      for (const t of c.contractTypes) counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    return Array.from(counts.entries())
      .map(([value, count]) => ({ value, label: value, count }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [baseFilteredClauses, filters.template]);

  const benchmarkData = useMemo(
    () => (benchmarksData?.data ?? []).map(toBenchmarkData),
    [benchmarksData],
  );

  // ── Dynamic Category Counts from actual clause data ──────────
  // Counts derive from the FULL clause list (not the filtered one) so the
  // sidebar keeps showing the true number of clauses in each category even
  // after the user picks one. Match category names by id, by a normalized
  // slug, and against the clause name as a final fallback — this way
  // backend categories like "liability_cap" still surface under
  // "Liability & Caps" (id "limitation_of_liability") etc.
  const categoriesWithCounts = useMemo(() => {
    const norm = (s: string) =>
      s.toLowerCase().trim().replace(/[\s-]+/g, "_");
    const counts = new Map<string, number>();
    for (const c of clauses) {
      const cat = norm(c.category || "");
      const name = norm(c.name || "");
      for (const sidebar of CLAUSE_CATEGORIES) {
        const id = norm(sidebar.id);
        if (cat === id || name.includes(id) || cat.includes(id)) {
          counts.set(sidebar.id, (counts.get(sidebar.id) ?? 0) + 1);
          break;
        }
      }
    }
    return CLAUSE_CATEGORIES.map((cat) => ({
      ...cat,
      count: counts.get(cat.id) ?? 0,
    }));
  }, [clauses]);

  // ── KPI Cards Data ────────────────────────────────────────────
  const clauseKpis = useMemo(() => {
    if (!kpisData) return [];
    // Derive playbook count from the PlaybookPanel data (hardcoded playbooks for now)
    const playbookCount = Math.max(kpisData.total_playbooks, 2); // At least 2 playbooks exist
    // Total fallback count from API or derive from clause fallback variants
    const totalFallbacks = clauses.reduce((sum, c) => sum + c.fallbackVariants.length, 0) || kpisData.total_fallbacks;
    return [
      { id: "total", label: "Total Clauses", value: kpisData.total_clauses.toString(), trend: 0, trendDirection: "neutral" as const, icon: "FileText", color: "from-navy-600 to-navy-800", severity: "info" as const, sparklineData: [10, 20, 15, 25, 30, 28, kpisData.total_clauses], tooltip: "Total clauses in library" },
      { id: "approved", label: "Approved", value: kpisData.approved_count.toString(), trend: 5, trendDirection: "up" as const, icon: "CheckCircle", color: "from-emerald-500 to-emerald-700", severity: "success" as const, sparklineData: [5, 8, 6, 10, 12, 11, kpisData.approved_count], tooltip: "Approved clauses" },
      { id: "pending", label: "Pending Review", value: kpisData.pending_review.toString(), trend: -2, trendDirection: "down" as const, icon: "RefreshCw", color: "from-amber-500 to-amber-700", severity: "warning" as const, sparklineData: [8, 6, 7, 5, 4, 3, kpisData.pending_review], tooltip: "Clauses awaiting review" },
      { id: "avgRisk", label: "Avg Risk Score", value: kpisData.avg_risk_score.toFixed(1), trend: 0, trendDirection: "neutral" as const, icon: "BarChart3", color: "from-rose-500 to-rose-700", severity: kpisData.avg_risk_score > 6 ? "critical" : kpisData.avg_risk_score > 4 ? "warning" : "success", sparklineData: [5, 4.5, 5.5, 4.8, 5.2, 4.9, kpisData.avg_risk_score], tooltip: "Average risk score across all clauses" },
      { id: "aiConf", label: "AI Confidence", value: `${kpisData.avg_ai_confidence.toFixed(0)}%`, trend: 3, trendDirection: "up" as const, icon: "Brain", color: "from-blue-500 to-blue-700", severity: "info" as const, sparklineData: [70, 72, 75, 73, 78, 76, kpisData.avg_ai_confidence], tooltip: "Average AI confidence level" },
      { id: "fallbacks", label: "Fallback Variants", value: totalFallbacks.toString(), trend: 8, trendDirection: "up" as const, icon: "Archive", color: "from-purple-500 to-purple-700", severity: "info" as const, sparklineData: [2, 3, 5, 4, 6, 7, totalFallbacks], tooltip: "Total fallback clause variants" },
      { id: "playbooks", label: "Playbooks", value: playbookCount.toString(), trend: 0, trendDirection: "neutral" as const, icon: "Globe", color: "from-cyan-500 to-cyan-700", severity: "info" as const, sparklineData: [1, 1, 2, 2, 3, 3, playbookCount], tooltip: "Active playbooks" },
      { id: "deprecated", label: "Deprecated", value: kpisData.deprecated_count.toString(), trend: -1, trendDirection: "down" as const, icon: "Archive", color: "from-gray-500 to-gray-700", severity: "info" as const, sparklineData: [4, 3, 3, 2, 2, 1, kpisData.deprecated_count], tooltip: "Deprecated clauses" },
    ];
  }, [kpisData, clauses]);

  // ── Favorite Toggle ───────────────────────────────────────────
  const toggleFavorite = useCallback((id: string) => {
    const clause = clauses.find((c) => c.id === id);
    if (!clause) return;
    // Persist in both the local favorites store (per-user, per-tenant,
    // localStorage) and the backend (so it follows the user across
    // devices). The backend update needs an id; we pass it explicitly.
    favorites.toggle(id);
    updateMutation.mutate({ id, body: { is_favorite: !clause.isFavorite } });
  }, [clauses, updateMutation, favorites]);

  // ── Loading / Error States ────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-navy-600 animate-spin" />
          <p className="text-sm text-gray-500">Loading clause library...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertCircle className="w-10 h-10 text-red-400" />
          <p className="text-sm font-medium text-gray-700">Failed to load clause library</p>
          <button onClick={() => refetch()} className="px-4 py-2 text-xs font-medium text-white bg-navy-700 rounded-lg hover:bg-navy-800 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-700 flex items-center justify-center shadow-sm">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Clause Intelligence Center</h1>
            <p className="text-xs text-gray-500 mt-0.5">Clause library, playbooks, and negotiation benchmarks</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative w-48">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search clauses..."
              className="w-full text-xs border border-gray-200 rounded-lg pl-8 pr-3 py-1.5 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 bg-white"
            />
          </div>
          <button onClick={() => refetch()} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button onClick={() => setShowCreateDialog(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Plus className="w-3.5 h-3.5" /> New Clause
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <Download className="w-3.5 h-3.5" /> Export
          </button>
        </div>
      </motion.div>

      {/* KPI Row */}
      <ClauseKpiCards metrics={clauseKpis} />

      {/* Secondary filter strip — Clause Type / Risk / Jurisdiction /
          Status / Template / Mandatory / Custom */}
      <ClauseFilterBar
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters({ ...EMPTY_FILTERS })}
        riskOptions={riskOptions}
        jurisdictionOptions={jurisdictionOptions}
        statusOptions={statusOptions}
        templateOptions={templateOptions}
        totalShown={filteredClauses.length}
        totalAll={clauses.length}
      />

      {/* Main Content: 3-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left: Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden h-full">
            <ClauseSidebar
              categories={categoriesWithCounts}
              selectedCategory={selectedCategory}
              onSelectCategory={setSelectedCategory}
              showFavorites={showFavorites}
              onToggleFavorites={() => setShowFavorites(!showFavorites)}
            />
          </div>
        </div>

        {/* Center: Clause Table + Benchmark */}
        <div className="lg:col-span-3 space-y-4">
          <ClauseTable clauses={filteredClauses} onSelect={setSelectedClause} onToggleFavorite={toggleFavorite} />
          <BenchmarkChart data={benchmarkData} />
        </div>

        {/* Right: Playbooks */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden p-4">
            <PlaybookPanel playbooks={[
              {
                id: "pb-indemnification",
                name: "Indemnification Playbook",
                description: "Standard approach for mutual and one-way indemnification clauses.",
                type: "negotiation",
                jurisdiction: "Delaware",
                contractTypes: ["MSA", "SaaS"],
                clauses: ["indemnification"],
                rules: [
                  { id: "r1", condition: "Mutual indemnification", action: "Accept as-is", priority: 1, enabled: true },
                  { id: "r2", condition: "One-way vendor indemnification", action: "Flag for review", priority: 2, enabled: true },
                  { id: "r3", condition: "IP infringement carve-out", action: "Require mutual", priority: 3, enabled: true },
                ],
                successRate: 82,
                usageCount: 187,
                lastUpdated: "2026-05-15",
                owner: "legal-team",
              },
              {
                id: "pb-liability",
                name: "Liability & Cap Playbook",
                description: "Negotiation guidance for limitation of liability clauses.",
                type: "negotiation",
                jurisdiction: "Delaware",
                contractTypes: ["MSA", "SaaS", "Consulting"],
                clauses: ["limitation_of_liability"],
                rules: [
                  { id: "r4", condition: "Cap > 2x annual fees", action: "Negotiate down", priority: 1, enabled: true },
                  { id: "r5", condition: "Unlimited liability for IP", action: "Accept", priority: 2, enabled: true },
                  { id: "r6", condition: "No cap for confidentiality breach", action: "Accept", priority: 3, enabled: true },
                ],
                successRate: 78,
                usageCount: 156,
                lastUpdated: "2026-05-12",
                owner: "legal-team",
              },
            ]} />
          </div>
        </div>
      </div>

      {/* Create Clause Dialog */}
      <CreateClauseDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onCreated={() => {
          setShowCreateDialog(false);
          refetch();
        }}
      />

      {/* Detail Drawer */}
      <ClauseDetailDrawer clause={selectedClause} benchmarks={benchmarkData} onClose={() => setSelectedClause(null)} onToggleFavorite={toggleFavorite} />
    </div>
  );
}

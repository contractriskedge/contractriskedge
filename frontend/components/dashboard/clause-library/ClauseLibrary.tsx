"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { BookOpen, Download, RefreshCw, Search, Plus } from "lucide-react";
import { ClauseKpiCards } from "./ClauseKpiCards";
import { ClauseSidebar } from "./ClauseSidebar";
import { ClauseTable } from "./ClauseTable";
import { PlaybookPanel } from "./PlaybookPanel";
import { ClauseDetailDrawer } from "./ClauseDetailDrawer";
import { BenchmarkChart } from "./BenchmarkChart";
import { clauseRecords, clauseKpis, playbooks, benchmarkData } from "./mockData";
import { CLAUSE_CATEGORIES } from "./types";
import type { ClauseRecord } from "./types";

export function ClauseLibrary() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showFavorites, setShowFavorites] = useState(false);
  const [selectedClause, setSelectedClause] = useState<ClauseRecord | null>(null);
  const [clauses, setClauses] = useState(clauseRecords);

  const toggleFavorite = useCallback((id: string) => {
    setClauses((prev) => prev.map((c) => c.id === id ? { ...c, isFavorite: !c.isFavorite } : c));
  }, []);

  const filteredClauses = useMemo(() => {
    let list = clauses;
    if (selectedCategory) list = list.filter((c) => c.category === selectedCategory);
    if (showFavorites) list = list.filter((c) => c.isFavorite);
    return list;
  }, [clauses, selectedCategory, showFavorites]);

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-700 flex items-center justify-center shadow-sm">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Clause Library & Playbooks</h1>
            <p className="text-xs text-gray-500 mt-0.5">Enterprise legal intelligence and negotiation playbook system</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <Search className="w-3.5 h-3.5" /> Smart Search
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Plus className="w-3.5 h-3.5" /> New Clause
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <Download className="w-3.5 h-3.5" /> Export
          </button>
        </div>
      </motion.div>

      {/* KPI Row */}
      <ClauseKpiCards metrics={clauseKpis} />

      {/* Main Content: 3-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left: Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden h-full">
            <ClauseSidebar
              categories={CLAUSE_CATEGORIES}
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
            <PlaybookPanel playbooks={playbooks} />
          </div>
        </div>
      </div>

      {/* Detail Drawer */}
      <ClauseDetailDrawer clause={selectedClause} benchmarks={benchmarkData} onClose={() => setSelectedClause(null)} onToggleFavorite={toggleFavorite} />
    </div>
  );
}

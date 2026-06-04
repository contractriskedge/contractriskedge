"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Share2, Download, RefreshCw, Search, CheckCircle2 } from "lucide-react";
import { GraphKpiCards } from "./GraphKpiCards";
import { GraphCanvas } from "./GraphCanvas";
import { RelationshipAiInsights } from "./AiInsights";
import { NodeDetailDrawer } from "./NodeDetailDrawer";
import { GraphFilterBar } from "./GraphFilterBar";
import { RelationshipTimeline } from "./Timeline";
import type { GraphNodeData, GraphMode } from "./types";

const mockGraphData = { nodes: [], edges: [] };
const graphKpis = [];
const relationshipInsights = [];
const timelineEvents = [];

export function RelationshipGraph() {
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [graphMode, setGraphMode] = useState<GraphMode>("relationship");
  const [filters, setFilters] = useState({ vendor: "", type: "", riskLevel: "" });
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [graphKey, setGraphKey] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toast, setToast] = useState<{ message: string; visible: boolean }>({ message: "", visible: false });

  const showToast = useCallback((message: string) => {
    setToast({ message, visible: true });
    setTimeout(() => setToast({ message: "", visible: false }), 2000);
  }, []);

  const handleFilterChange = useCallback((key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ vendor: "", type: "", riskLevel: "" });
  }, []);

  const handleNodeSelect = useCallback((node: GraphNodeData | null) => {
    setSelectedNode(node);
  }, []);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setGraphKey((k) => k + 1);
    setSelectedNode(null);
    showToast("Graph refreshed");
    setTimeout(() => setIsRefreshing(false), 600);
  }, [showToast]);

  const handleSmartSearch = useCallback(() => {
    setIsSearchOpen((prev) => !prev);
  }, []);

  const handleExportGraph = useCallback(() => {
    // Export SVG content as SVG file
    const svgEl = document.querySelector("#graph-canvas-svg");
    if (svgEl) {
      const serializer = new XMLSerializer();
      const svgContent = serializer.serializeToString(svgEl);
      const blob = new Blob([svgContent], { type: "image/svg+xml;charset=utf-8" });
      const link = document.createElement("a");
      link.download = `relationship-graph-${new Date().toISOString().slice(0, 10)}.svg`;
      link.href = URL.createObjectURL(blob);
      link.click();
      URL.revokeObjectURL(link.href);
      showToast("Graph exported as SVG");
    } else {
      showToast("No graph data to export");
    }
  }, [showToast]);

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-purple-800 flex items-center justify-center shadow-sm">
            <Share2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Contract Relationship Intelligence</h1>
            <p className="text-xs text-gray-500 mt-0.5">Enterprise dependency mapping and relationship analysis</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSmartSearch}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
              isSearchOpen
                ? "bg-navy-700 text-white border-navy-700"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            <Search className="w-3.5 h-3.5" /> Smart Search
          </button>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} /> Refresh
          </button>
          <button
            onClick={handleExportGraph}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" /> Export Graph
          </button>
        </div>
      </motion.div>

      {/* Smart Search Bar */}
      {isSearchOpen && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search contracts, vendors, clauses..."
              className="w-full text-sm border border-gray-200 rounded-lg pl-9 pr-3 py-2 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
              autoFocus
            />
          </div>
          <button
            onClick={() => { setIsSearchOpen(false); setSearchQuery(""); }}
            className="px-3 py-2 text-xs font-medium text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </motion.div>
      )}

      {/* KPI Row */}
      <GraphKpiCards metrics={graphKpis} />

      {/* Filter Bar + Graph Modes */}
      <GraphFilterBar
        filters={filters}
        onChange={handleFilterChange}
        onReset={resetFilters}
        mode={graphMode}
        onModeChange={setGraphMode}
      />

      {/* Main Content: Graph + Side Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left: AI Insights */}
        <div className="lg:col-span-1 space-y-4">
          <RelationshipAiInsights insights={relationshipInsights} />
          <RelationshipTimeline events={timelineEvents} />
        </div>

        {/* Center: Graph */}
        <div className="lg:col-span-3">
          <GraphCanvas
            key={graphKey}
            data={mockGraphData}
            mode={graphMode}
            onNodeSelect={handleNodeSelect}
            selectedNodeId={selectedNode?.id || null}
            filterVendor={filters.vendor}
            filterType={filters.type}
            filterRisk={filters.riskLevel}
          />
        </div>
      </div>

      {/* Detail Drawer */}
      <NodeDetailDrawer node={selectedNode} onClose={() => setSelectedNode(null)} />

      {/* Toast Notification */}
      <AnimatePresence>
        {toast.visible && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 bg-navy-900 text-white text-xs font-medium rounded-lg shadow-lg"
          >
            <CheckCircle2 className="w-4 h-4 text-green-400" />
            {toast.message}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

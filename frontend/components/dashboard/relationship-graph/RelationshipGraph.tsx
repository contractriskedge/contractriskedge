"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Share2, Download, RefreshCw, Search } from "lucide-react";
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

  const handleFilterChange = useCallback((key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ vendor: "", type: "", riskLevel: "" });
  }, []);

  const handleNodeSelect = useCallback((node: GraphNodeData | null) => {
    setSelectedNode(node);
  }, []);

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
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <Search className="w-3.5 h-3.5" /> Smart Search
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" /> Export Graph
          </button>
        </div>
      </motion.div>

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
    </div>
  );
}

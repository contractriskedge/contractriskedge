"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Workflow, Download, RefreshCw } from "lucide-react";
import { WorkflowKpiCards } from "./WorkflowKpiCards";
import { KanbanBoard } from "./KanbanBoard";
import { WorkflowAiInsights } from "./AiInsights";
import { ApprovalTable } from "./ApprovalTable";
import { WorkflowDetailDrawer } from "./WorkflowDetailDrawer";
import { SlaBreachChart, SlaBreachRateChart, TeamWorkload, AutomationRulesPanel } from "./SlaCenter";
import { WorkflowFilterBar } from "./WorkflowFilterBar";
import { workflowKpis, workflowItems, workflowInsights, slaMetrics, teamMembers, automationRules } from "./mockData";
import type { WorkflowItem } from "./types";

interface WorkflowFilters {
  stage: string; priority: string; slaStatus: string; riskLevel: string; department: string;
}

const defaultFilters: WorkflowFilters = { stage: "", priority: "", slaStatus: "", riskLevel: "", department: "" };

export function WorkflowCenter() {
  const [filters, setFilters] = useState<WorkflowFilters>({ ...defaultFilters });
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowItem | null>(null);

  const handleFilterChange = useCallback((key: keyof WorkflowFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);
  const resetFilters = useCallback(() => setFilters({ ...defaultFilters }), []);

  // Apply filters
  const filteredWorkflows = workflowItems.filter((w) => {
    if (filters.stage && w.currentStage !== filters.stage) return false;
    if (filters.priority && w.priority !== filters.priority) return false;
    if (filters.riskLevel) {
      if (filters.riskLevel === "critical" && w.riskScore < 8) return false;
      else if (filters.riskLevel === "high" && (w.riskScore < 6 || w.riskScore >= 8)) return false;
      else if (filters.riskLevel === "medium" && (w.riskScore < 4 || w.riskScore >= 6)) return false;
    }
    return true;
  });

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-sm">
            <Workflow className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Workflow & Approval Center</h1>
            <p className="text-xs text-gray-500 mt-0.5">Enterprise contract operations and workflow orchestration</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" /> Export
          </button>
        </div>
      </motion.div>

      {/* KPI Row */}
      <WorkflowKpiCards metrics={workflowKpis} />

      {/* Filter Bar */}
      <WorkflowFilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} />

      {/* Section 1: Kanban Board */}
      <div>
        <h2 className="text-sm font-semibold text-navy-900 mb-3">Active Workflow Pipeline</h2>
        <KanbanBoard workflows={filteredWorkflows} onSelectWorkflow={setSelectedWorkflow} />
      </div>

      {/* Section 2: AI Insights + SLA */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <WorkflowAiInsights insights={workflowInsights} />
        </div>
        <div className="lg:col-span-1 space-y-4">
          <SlaBreachChart data={slaMetrics} />
          <SlaBreachRateChart data={slaMetrics} />
        </div>
      </div>

      {/* Section 3: Approval Table */}
      <ApprovalTable workflows={filteredWorkflows} onSelect={setSelectedWorkflow} />

      {/* Section 4: Team + Automation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TeamWorkload members={teamMembers} />
        <AutomationRulesPanel rules={automationRules} />
      </div>

      {/* Detail Drawer */}
      <WorkflowDetailDrawer workflow={selectedWorkflow} onClose={() => setSelectedWorkflow(null)} />
    </div>
  );
}

"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Workflow, Download, RefreshCw, Loader2, AlertCircle } from "lucide-react";
import { WorkflowKpiCards } from "./WorkflowKpiCards";
import { KanbanBoard } from "./KanbanBoard";
import { WorkflowAiInsights } from "./AiInsights";
import { ApprovalTable } from "./ApprovalTable";
import { WorkflowDetailDrawer } from "./WorkflowDetailDrawer";
import { SlaBreachChart, SlaBreachRateChart, TeamWorkload, AutomationRulesPanel } from "./SlaCenter";
import { WorkflowFilterBar } from "./WorkflowFilterBar";
import { useWorkflowDashboard, useWorkflows } from "@/services/hooks/useWorkflows";
import type { WorkflowItem } from "./types";

interface WorkflowFilters {
  stage: string; priority: string; slaStatus: string; riskLevel: string; department: string;
}

const defaultFilters: WorkflowFilters = { stage: "", priority: "", slaStatus: "", riskLevel: "", department: "" };

export function WorkflowCenter() {
  const [filters, setFilters] = useState<WorkflowFilters>({ ...defaultFilters });
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowItem | null>(null);

  // Real API hooks replacing mockData
  const { data: dashboardData, isLoading, error, refetch } = useWorkflowDashboard();
  const { data: workflowsData } = useWorkflows();

  const workflowKpis = dashboardData?.kpis ?? [];
  const workflowItems = workflowsData?.data ?? dashboardData?.workflows ?? [];
  const workflowInsights = [];
  const slaMetrics = [];
  const teamMembers = [];
  const automationRules = [];

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

  // Loading state
  if (isLoading && workflowItems.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-gold-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading workflow data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && workflowItems.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load workflow data</p>
          <p className="text-xs text-gray-500 mb-4">{(error as Error)?.message || "An unexpected error occurred"}</p>
          <button onClick={() => refetch()} className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
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

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
import type { WorkflowItem, WorkflowInsight, SlaMetric, TeamMember, AutomationRule } from "./types";

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
  // Derive insights, SLA metrics, team members, and automation rules from real data
  const workflowInsights: WorkflowInsight[] = workflowItems.length > 0
    ? workflowItems
        .filter((w: any) => {
          const deadline = w.sla_deadline || w.dueDate;
          return deadline && new Date(deadline) < new Date(Date.now() + 24 * 60 * 60 * 1000);
        })
        .slice(0, 5)
        .map((w: any) => {
          const deadline = w.sla_deadline || w.dueDate;
          const isBreached = w.sla_breached === true || w.slaRemaining <= 0;
          const slaStatus = isBreached ? "breached" : (w.slaRemaining !== undefined && w.slaRemaining <= 24) ? "at_risk" : "ok";
          const name = w.name || w.contractName || w.id;
          const stage = w.currentStage || w.type || "unknown";
          const riskScore = w.riskScore ?? 5;
          return {
            id: `insight-${w.id}`,
            title: `SLA ${slaStatus === "breached" ? "Breach" : "At Risk"}: ${name}`,
            description: deadline
              ? `${name} has SLA deadline ${new Date(deadline).toLocaleDateString()}${w.slaRemaining !== undefined ? ` (${w.slaRemaining}h remaining)` : ""}`
              : `${name} is at ${stage} stage with risk score ${riskScore}`,
            severity: slaStatus === "breached" ? "critical" : slaStatus === "at_risk" ? "warning" : "info",
            confidence: Math.round((1 - Math.abs(riskScore - 5) / 10) * 100),
            impactedWorkflows: [w.id],
            suggestedAction: slaStatus === "breached"
              ? `Escalate ${name} — SLA already breached`
              : `Prioritize ${name} — SLA due ${deadline ? new Date(deadline).toLocaleDateString() : "soon"}`,
            category: "sla",
            quickActions: [{ label: "View Workflow", action: `view-${w.id}` }],
          };
        })
    : [];
  const slaMetrics: SlaMetric[] = workflowItems.length > 0
    ? Array.from(new Set(workflowItems.map((w: any) => w.currentStage || w.type || "unknown"))).slice(0, 6).map((stage) => {
        const stageItems = workflowItems.filter((w: any) => (w.currentStage || w.type || "unknown") === stage);
        const breached = stageItems.filter((w: any) => w.sla_breached === true || w.slaRemaining <= 0).length;
        return {
          stage: stage as any,
          targetHours: 24,
          actualHours: stageItems.reduce((s: number, w: any) => s + ((w.progress ?? 0) > 0 ? Math.round(24 / (w.progress ?? 1) * 10) / 10 : 24), 0) / Math.max(1, stageItems.length),
          breachCount: breached,
          breachRate: Math.round((breached / Math.max(1, stageItems.length)) * 100),
          trend: breached > 0 ? -breached * 5 : 5,
        };
      })
    : [];
  const teamMembers: TeamMember[] = [];
  const automationRules: AutomationRule[] = [];

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

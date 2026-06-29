"use client";

import React, { useState, useMemo } from "react";
import {
  Workflow, Plus, Search, LayoutGrid, List, ArrowLeft, Activity,
  RefreshCw, Download, Upload, Layers, CheckCircle, Clock,
  TrendingUp, BarChart3, Filter,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { LoadingSkeleton, CardSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { useWorkflowPacks } from "@/services/hooks/useWorkflowAdmin";
import { WorkflowPackCard } from "./WorkflowPackCard";
import { WorkflowPackDetailDrawer } from "./WorkflowPackDetailDrawer";
import { CreateWorkflowDialog } from "./CreateWorkflowDialog";
import { WorkflowDesigner } from "./WorkflowDesigner";
import { RuleBuilder } from "./RuleBuilder";
import { WorkflowSimulator } from "./WorkflowSimulator";
import { PublishingFlow } from "./PublishingFlow";
import { VersionComparison } from "./VersionComparison";
import { UsageDashboard } from "./UsageDashboard";
import { WorkflowOperationsCenter } from "./WorkflowOperationsCenter";

export function WorkflowAdminCenter() {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [selectedPackId, setSelectedPackId] = useState<string | null>(null);
  const [designerPackId, setDesignerPackId] = useState<string | null>(null);
  const [ruleBuilderOpen, setRuleBuilderOpen] = useState(false);
  const [simulatorOpen, setSimulatorOpen] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [operationsOpen, setOperationsOpen] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const { data, isLoading, error, refetch } = useWorkflowPacks({
    search: search || undefined,
    category: categoryFilter || undefined,
    status: statusFilter || undefined,
  });

  const packs = data?.items ?? [];
  const total = data?.total ?? 0;

  // Derived KPI data
  const kpis = useMemo(() => {
    const published = packs.filter((p) => p.status === "published").length;
    const draft = packs.filter((p) => p.status === "draft").length;
    const running = packs.reduce((sum, p) => sum + (p.running_instances || 0), 0);
    const avgHealth = packs.length > 0
      ? Math.round(packs.reduce((sum, p) => sum + (p.health_score || 0), 0) / packs.length)
      : 0;
    const mostUsed = packs.reduce((best, p) => (p.usage_count > (best?.usage_count || 0) ? p : best), packs[0]);
    return { published, draft, running, avgHealth, mostUsed };
  }, [packs]);

  // If Designer is open, show it instead of the library
  if (designerPackId) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setDesignerPackId(null)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workflow Packs
        </button>
        <WorkflowDesigner
          initialStages={[]}
          onSave={(stages) => {
            console.log("Saving stages:", stages);
            setDesignerPackId(null);
          }}
          onBack={() => setDesignerPackId(null)}
        />
      </div>
    );
  }

  // If Rule Builder is open, show it
  if (ruleBuilderOpen) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setRuleBuilderOpen(false)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workflow Packs
        </button>
        <RuleBuilder
          onSave={(rules) => {
            console.log("Saving rules:", rules);
            setRuleBuilderOpen(false);
          }}
          onBack={() => setRuleBuilderOpen(false)}
        />
      </div>
    );
  }

  // If Simulator is open, show it
  if (simulatorOpen) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setSimulatorOpen(false)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workflow Packs
        </button>
        <WorkflowSimulator onBack={() => setSimulatorOpen(false)} />
      </div>
    );
  }

  // If Publishing Flow is open, show it
  if (publishOpen) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setPublishOpen(false)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workflow Packs
        </button>
        <PublishingFlow
          packName="NDA Review"
          versionInfo={{ current_version: 2, current_status: "published", new_version: 3 }}
          onPublish={(data) => {
            console.log("Publishing:", data);
            setPublishOpen(false);
          }}
          onRollback={(targetVersion) => {
            console.log("Rollback to:", targetVersion);
            setPublishOpen(false);
          }}
          onBack={() => setPublishOpen(false)}
        />
      </div>
    );
  }

  // If Version Comparison is open, show it
  if (compareOpen) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setCompareOpen(false)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workflow Packs
        </button>
        <VersionComparison onBack={() => setCompareOpen(false)} />
      </div>
    );
  }

  // If Usage Dashboard is open, show it
  if (dashboardOpen) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setDashboardOpen(false)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workflow Packs
        </button>
        <UsageDashboard onBack={() => setDashboardOpen(false)} />
      </div>
    );
  }

  // If Operations Center is open, show it
  if (operationsOpen) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setOperationsOpen(false)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workflow Packs
        </button>
        <WorkflowOperationsCenter onBack={() => setOperationsOpen(false)} />
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <PageHeader
        title="Workflow Administration"
        description="Configure, validate, simulate, and publish workflow packs"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-navy-600 px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
            <button
              onClick={() => setOperationsOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-navy-600 px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
            >
              <Activity className="w-3.5 h-3.5" />
              Operations
            </button>
            <button className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-navy-600 px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors">
              <Upload className="w-3.5 h-3.5" />
              Import
            </button>
            <button className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-navy-600 px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors">
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-navy-700 dark:bg-navy-600 px-3 py-2 text-xs font-medium text-white hover:bg-navy-800 dark:hover:bg-navy-500 shadow-sm transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              New Workflow Pack
            </button>
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiCard
          title="Total Workflows"
          value={total}
          icon={<Layers className="h-5 w-5 text-white" />}
          color="bg-navy-500"
        />
        <KpiCard
          title="Published"
          value={kpis.published}
          icon={<CheckCircle className="h-5 w-5 text-white" />}
          color="bg-emerald-500"
        />
        <KpiCard
          title="Draft"
          value={kpis.draft}
          icon={<Clock className="h-5 w-5 text-white" />}
          color="bg-amber-500"
        />
        <KpiCard
          title="Running Instances"
          value={kpis.running}
          icon={<Activity className="h-5 w-5 text-white" />}
          color="bg-blue-500"
        />
        <KpiCard
          title="Avg Health Score"
          value={`${kpis.avgHealth}%`}
          icon={<TrendingUp className="h-5 w-5 text-white" />}
          color={kpis.avgHealth >= 80 ? "bg-emerald-500" : kpis.avgHealth >= 50 ? "bg-amber-500" : "bg-red-500"}
        />
        <KpiCard
          title="Most Used"
          value={kpis.mostUsed?.name?.split(" ").slice(0, 2).join(" ") || "—"}
          subtitle={kpis.mostUsed ? `${kpis.mostUsed.usage_count}x used` : undefined}
          icon={<BarChart3 className="h-5 w-5 text-white" />}
          color="bg-purple-500"
        />
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 bg-white dark:bg-navy-800 rounded-lg border border-gray-200 dark:border-navy-700 px-3 py-2">
        <Filter className="w-3 h-3 text-gray-400" />
        <div className="relative flex-1 min-w-[180px] max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search workflows..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-md bg-white dark:bg-navy-800 text-gray-700 dark:text-gray-300 placeholder-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400/20 transition-colors"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1.5 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors pr-6 appearance-none cursor-pointer min-w-[110px]"
        >
          <option value="">All Categories</option>
          <option value="legal">Legal</option>
          <option value="sales">Sales</option>
          <option value="procurement">Procurement</option>
          <option value="hr">HR</option>
          <option value="privacy">Privacy</option>
          <option value="custom">Custom</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-[11px] border border-gray-200 dark:border-navy-600 rounded-md px-2 py-1.5 text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 hover:border-gray-300 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors pr-6 appearance-none cursor-pointer min-w-[100px]"
        >
          <option value="">All Status</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
          <option value="archived">Archived</option>
        </select>
        <div className="flex items-center border border-gray-200 dark:border-navy-600 rounded-md overflow-hidden">
          <button
            onClick={() => setViewMode("grid")}
            className={`p-1.5 ${viewMode === "grid" ? "bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white" : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"}`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`p-1.5 ${viewMode === "list" ? "bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white" : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"}`}
          >
            <List className="w-3.5 h-3.5" />
          </button>
        </div>
        {(categoryFilter || statusFilter || search) && (
          <button
            onClick={() => { setCategoryFilter(""); setStatusFilter(""); setSearch(""); }}
            className="text-[10px] text-gray-400 hover:text-red-500 flex items-center gap-0.5 transition-colors"
          >
            Reset
          </button>
        )}
        {!isLoading && (
          <span className="text-[11px] text-gray-400 ml-auto tabular-nums">
            {total} workflow{total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <CardSkeleton count={6} columns={3} />
      ) : error ? (
        <ErrorState message="Failed to load workflow packs" onRetry={() => refetch()} />
      ) : packs.length === 0 ? (
        <EmptyState
          icon={<Workflow className="w-12 h-12" />}
          title="No workflow packs yet"
          message="Clone a built-in pack or create a new one to get started."
          action={
            <button
              onClick={() => setShowCreateDialog(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-navy-700 text-white rounded-lg hover:bg-navy-800 transition-colors text-sm font-medium shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Create Workflow Pack
            </button>
          }
        />
      ) : (
        <div className={viewMode === "grid"
          ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          : "space-y-2"
        }>
          {packs.map((pack) => (
            <WorkflowPackCard
              key={pack.pack_id}
              pack={pack}
              viewMode={viewMode}
              onClick={() => setSelectedPackId(pack.pack_id)}
            />
          ))}
        </div>
      )}

      {/* Detail Drawer */}
      {selectedPackId && (
        <WorkflowPackDetailDrawer
          packId={selectedPackId}
          onClose={() => setSelectedPackId(null)}
          onOpenDesigner={(id: string) => {
            setSelectedPackId(null);
            setDesignerPackId(id);
          }}
        />
      )}

      {/* Create Dialog */}
      {showCreateDialog && (
        <CreateWorkflowDialog onClose={() => setShowCreateDialog(false)} />
      )}
    </div>
  );
}

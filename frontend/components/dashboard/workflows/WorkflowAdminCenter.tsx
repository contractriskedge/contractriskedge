"use client";

import React, { useState, useMemo } from "react";
import {
  Workflow, Plus, Search, LayoutGrid, List, ArrowLeft, Activity,
  RefreshCw, Download, Upload, Layers, CheckCircle, Clock,
  TrendingUp, BarChart3, Filter, Archive,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { LoadingSkeleton, CardSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { useWorkflowPacks, useArchiveWorkflowPack, useCloneWorkflowPack, useRenameWorkflowPack } from "@/services/hooks/useWorkflowAdmin";
import { WorkflowPackCard } from "./WorkflowPackCard";
import { WorkflowPackDetailDrawer, type WorkflowPackTabId } from "./WorkflowPackDetailDrawer";
import { CreateWorkflowDialog } from "./CreateWorkflowDialog";
import { WorkflowOperationsCenter } from "./WorkflowOperationsCenter";
import { getHealthTier } from "./workflowHealthUtils";

export function WorkflowAdminCenter() {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [healthFilter, setHealthFilter] = useState<string>("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [selectedPackId, setSelectedPackId] = useState<string | null>(null);
  const [drawerInitialTab, setDrawerInitialTab] = useState<WorkflowPackTabId>("overview");
  const [operationsOpen, setOperationsOpen] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const { data, isLoading, error, refetch } = useWorkflowPacks({
    search: search || undefined,
    category: categoryFilter || undefined,
    status: statusFilter || undefined,
  });
  const archiveMutation = useArchiveWorkflowPack();
  const cloneMutation = useCloneWorkflowPack();
  const renameMutation = useRenameWorkflowPack();

  const allPacks = data?.items ?? [];

  // Client-side health filter (KPI drill-down)
  const packs = useMemo(() => {
    if (!healthFilter) return allPacks;
    return allPacks.filter((p) => getHealthTier(p.health_score ?? 0) === healthFilter);
  }, [allPacks, healthFilter]);

  const total = healthFilter ? packs.length : (data?.total ?? 0);

  const kpis = useMemo(() => {
    const published = allPacks.filter((p) => p.status === "published").length;
    const draft = allPacks.filter((p) => p.status === "draft").length;
    const archived = allPacks.filter((p) => p.status === "archived").length;
    const running = allPacks.reduce((sum, p) => sum + (p.running_instances || 0), 0);
    const avgHealth = allPacks.length > 0
      ? Math.round(allPacks.reduce((sum, p) => sum + (p.health_score || 0), 0) / allPacks.length)
      : 0;
    return { published, draft, archived, running, avgHealth };
  }, [allPacks]);

  const openPack = (packId: string, tab: WorkflowPackTabId = "overview") => {
    setDrawerInitialTab(tab);
    setSelectedPackId(packId);
  };

  const resetFilters = () => {
    setCategoryFilter("");
    setStatusFilter("");
    setHealthFilter("");
    setSearch("");
  };

  // Operations Center remains a separate operational view
  if (operationsOpen) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setOperationsOpen(false)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Workflow Library
        </button>
        <WorkflowOperationsCenter onBack={() => setOperationsOpen(false)} />
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-24">
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
            <button
              onClick={() => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.json';
                input.onchange = async (e) => {
                  const file = (e.target as HTMLInputElement).files?.[0];
                  if (!file) return;
                  try {
                    const formData = new FormData();
                    formData.append('file', file);
                    const res = await fetch('/api/v1/workflow-packs/import', {
                      method: 'POST',
                      headers: { 'Authorization': 'Bearer dev-token' },
                      body: formData,
                    });
                    if (res.ok) { refetch(); alert('Workflow imported successfully.'); }
                    else alert('Import failed.');
                  } catch { alert('Import failed.'); }
                };
                input.click();
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-navy-600 px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
            >
              <Upload className="w-3.5 h-3.5" />
              Import
            </button>
            <button
              onClick={async () => {
                if (packs.length === 0) { alert('No workflows to export.'); return; }
                try {
                  const res = await fetch('/api/v1/workflow-packs', {
                    headers: { 'Authorization': 'Bearer dev-token' },
                  });
                  const data = await res.json();
                  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `workflows-export-${new Date().toISOString().split('T')[0]}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                } catch { alert('Export failed.'); }
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-navy-600 px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
            >
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

      {/* KPI Cards — clickable drill-down to filtered views */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <KpiCard
          title="Total Workflows"
          value={data?.total ?? 0}
          icon={<Layers className="h-5 w-5 text-white" />}
          color="bg-navy-500"
          onClick={resetFilters}
        />
        <KpiCard
          title="Published"
          value={kpis.published}
          icon={<CheckCircle className="h-5 w-5 text-white" />}
          color="bg-emerald-500"
          onClick={() => { setHealthFilter(""); setStatusFilter("published"); }}
        />
        <KpiCard
          title="Draft"
          value={kpis.draft}
          icon={<Clock className="h-5 w-5 text-white" />}
          color="bg-amber-500"
          onClick={() => { setHealthFilter(""); setStatusFilter("draft"); }}
        />
        <KpiCard
          title="Running Instances"
          value={kpis.running}
          icon={<Activity className="h-5 w-5 text-white" />}
          color="bg-blue-500"
          onClick={() => setOperationsOpen(true)}
        />
        <KpiCard
          title="Avg Health Score"
          value={`${kpis.avgHealth}%`}
          icon={<TrendingUp className="h-5 w-5 text-white" />}
          color={kpis.avgHealth >= 80 ? "bg-emerald-500" : kpis.avgHealth >= 50 ? "bg-amber-500" : "bg-red-500"}
          onClick={() => {
            setStatusFilter("");
            setHealthFilter(kpis.avgHealth >= 80 ? "healthy" : kpis.avgHealth >= 50 ? "warning" : "critical");
          }}
        />
        <KpiCard
          title="Archived"
          value={kpis.archived}
          icon={<Archive className="h-5 w-5 text-white" />}
          color="bg-gray-500"
          onClick={() => { setHealthFilter(""); setStatusFilter("archived"); }}
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
        {(categoryFilter || statusFilter || healthFilter || search) && (
          <button
            onClick={resetFilters}
            className="text-[10px] text-gray-400 hover:text-red-500 flex items-center gap-0.5 transition-colors"
          >
            Reset
          </button>
        )}
        {!isLoading && (
          <span className="text-[11px] text-gray-400 ml-auto tabular-nums">
            {total} workflow{total !== 1 ? "s" : ""}
            {healthFilter && ` · ${healthFilter} health`}
          </span>
        )}
      </div>

      {/* Workflow Library */}
      {isLoading ? (
        <CardSkeleton count={6} columns={3} />
      ) : error ? (
        <ErrorState message="Failed to load workflow packs" onRetry={() => refetch()} />
      ) : packs.length === 0 ? (
        <EmptyState
          icon={<Workflow className="w-12 h-12" />}
          title={healthFilter || statusFilter || search ? "No matching workflows" : "No workflow packs yet"}
          message={
            healthFilter || statusFilter || search
              ? "Try adjusting your filters or reset to see all workflows."
              : "Clone a built-in pack or create a new one to get started."
          }
          action={
            healthFilter || statusFilter || search ? (
              <button
                onClick={resetFilters}
                className="inline-flex items-center gap-2 px-4 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
              >
                Reset Filters
              </button>
            ) : (
              <button
                onClick={() => setShowCreateDialog(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-navy-700 text-white rounded-lg hover:bg-navy-800 transition-colors text-sm font-medium shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Create Workflow Pack
              </button>
            )
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
              onClick={() => openPack(pack.pack_id)}
              onArchive={(packId: string) => {
                if (confirm('Archive this workflow pack? It can be restored later.')) {
                  archiveMutation.mutate(packId);
                }
              }}
              onClone={(packId: string) => {
                const name = prompt('Enter a name for the cloned workflow pack:', 'Copy');
                if (name) cloneMutation.mutate({ packId, name });
              }}
              onRename={(packId: string) => {
                const pack = allPacks.find((p) => p.pack_id === packId);
                const newName = prompt('Enter a new name for this workflow pack:', pack?.name || '');
                if (newName && newName !== pack?.name) renameMutation.mutate({ packId, name: newName });
              }}
            />
          ))}
        </div>
      )}

      {selectedPackId && (
        <WorkflowPackDetailDrawer
          key={`${selectedPackId}-${drawerInitialTab}`}
          packId={selectedPackId}
          initialTab={drawerInitialTab}
          onClose={() => setSelectedPackId(null)}
        />
      )}

      {showCreateDialog && (
        <CreateWorkflowDialog onClose={() => setShowCreateDialog(false)} />
      )}
    </div>
  );
}

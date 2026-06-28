"use client";

import React, { useState } from "react";
import { Workflow, Plus, Search, LayoutGrid, List, ArrowLeft, Activity } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
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

  // If Designer is open, show it instead of the library
  if (designerPackId) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setDesignerPackId(null)}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
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
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
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
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
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
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
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
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
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
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
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
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Workflow Packs
        </button>
        <WorkflowOperationsCenter onBack={() => setOperationsOpen(false)} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Workflow Administration"
        description="Configure, validate, simulate, and publish workflow packs"
        actions={
          <div className="flex gap-2">
            <button
              onClick={() => setOperationsOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-navy-800 text-gray-300 rounded-lg hover:bg-navy-700 transition-colors"
            >
              <Activity className="w-4 h-4" />
              Operations
            </button>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 transition-colors font-medium"
            >
              <Plus className="w-4 h-4" />
              New Workflow Pack
            </button>
          </div>
        }
      />

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search packs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-navy-800/50 border border-navy-600 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
          />
        </div>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-2 bg-navy-800/50 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
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
          className="px-3 py-2 bg-navy-800/50 border border-navy-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-gold-500/50"
        >
          <option value="">All Status</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
          <option value="archived">Archived</option>
        </select>

        <div className="flex items-center border border-navy-600 rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode("grid")}
            className={`p-2 ${viewMode === "grid" ? "bg-gold-500/20 text-gold-400" : "text-gray-400 hover:text-gray-200"}`}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`p-2 ${viewMode === "list" ? "bg-gold-500/20 text-gold-400" : "text-gray-400 hover:text-gray-200"}`}
          >
            <List className="w-4 h-4" />
          </button>
        </div>

        {(categoryFilter || statusFilter || search) && (
          <button
            onClick={() => { setCategoryFilter(""); setStatusFilter(""); setSearch(""); }}
            className="text-sm text-gold-400 hover:text-gold-300"
          >
            Reset filters
          </button>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <LoadingSkeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      ) : error ? (
        <ErrorState message="Failed to load workflow packs" onRetry={() => refetch()} />
      ) : packs.length === 0 ? (
        <EmptyState
          icon={<Workflow className="w-12 h-12" />}
          title="No workflow packs yet"
          description='Clone a built-in pack or create a new one to get started.'
          action={
            <button
              onClick={() => setShowCreateDialog(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gold-500 text-navy-900 rounded-lg hover:bg-gold-400 transition-colors font-medium"
            >
              <Plus className="w-4 h-4" />
              Create Workflow Pack
            </button>
          }
        />
      ) : (
        <>
          <div className="text-sm text-gray-400">
            {total} pack{total !== 1 ? "s" : ""}
          </div>
          <div className={viewMode === "grid"
            ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
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
        </>
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

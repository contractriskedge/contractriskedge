"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  X, Workflow, Edit, Play, CheckCircle, Clock, AlertTriangle,
  FileJson, Download, Copy, Archive, BarChart3, GitCompare,
  Layers, Users, FileText, Activity, TrendingUp, Shield,
  ExternalLink, Brain, Settings, History,
} from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { useWorkflowPack, useVersions } from "@/services/hooks/useWorkflowAdmin";

interface Props {
  packId: string;
  onClose: () => void;
  onOpenDesigner?: (packId: string) => void;
}

type TabId = "overview" | "designer" | "rules" | "simulator" | "versions" | "analytics" | "timeline" | "history" | "settings";

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ElementType;
}

const TABS: TabDef[] = [
  { id: "overview", label: "Overview", icon: FileText },
  { id: "designer", label: "Designer", icon: Edit },
  { id: "rules", label: "Rules", icon: Brain },
  { id: "simulator", label: "Simulator", icon: Play },
  { id: "versions", label: "Versions", icon: GitCompare },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "timeline", label: "Timeline", icon: Activity },
  { id: "history", label: "History", icon: History },
  { id: "settings", label: "Settings", icon: Settings },
];

function TabBtn({ label, icon: Icon, active, onClick }: { label: string; icon: React.ElementType; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md whitespace-nowrap transition-all ${
        active ? "bg-navy-700 text-white shadow-sm" : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
      }`}
    >
      <Icon className="w-3 h-3" />
      {label}
    </button>
  );
}

export function WorkflowPackDetailDrawer({ packId, onClose, onOpenDesigner }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const { data: pack, isLoading, error } = useWorkflowPack(packId);
  const { data: versions } = useVersions(packId);

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, x: 380 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 380 }}
        transition={{ type: "spring", damping: 25, stiffness: 250 }}
        className="fixed right-0 top-0 bottom-0 w-[70vw] max-w-4xl bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2 min-w-0">
            <Workflow className="w-4 h-4 text-navy-600 flex-shrink-0" />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-navy-900 truncate">
                {isLoading ? "Loading..." : pack?.name ?? "Workflow Pack"}
              </h3>
              {pack && (
                <p className="text-[10px] text-gray-500 truncate">
                  v{pack.version} · {pack.category} · {pack.owner || "—"}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onOpenDesigner?.(packId)}
              className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700 transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
              Full Workspace
            </button>
            <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Quick Actions Bar */}
        {pack && (
          <div className="flex items-center gap-2 px-5 py-2.5 border-b border-gray-100 bg-gray-50/50">
            <button className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700 transition-colors shadow-sm">
              <Edit className="w-3 h-3" /> Designer
            </button>
            <button className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
              <Play className="w-3 h-3" /> Simulator
            </button>
            <button className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
              <CheckCircle className="w-3 h-3" /> Validate
            </button>
            <button className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition-colors shadow-sm">
              <Layers className="w-3 h-3" /> Publish
            </button>
            <span className="text-[10px] text-gray-300 mx-1">|</span>
            <button className="inline-flex items-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors">
              <Copy className="w-3 h-3" /> Clone
            </button>
            <button className="inline-flex items-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors">
              <Download className="w-3 h-3" /> Export
            </button>
            <button className="inline-flex items-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors">
              <FileJson className="w-3 h-3" /> Import
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="px-4 py-2 border-b border-gray-100 flex gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <TabBtn
              key={tab.id}
              label={tab.label}
              icon={tab.icon}
              active={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
            />
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              <LoadingSkeleton className="h-24 rounded-lg" />
              <LoadingSkeleton className="h-48 rounded-lg" />
              <LoadingSkeleton className="h-32 rounded-lg" />
            </div>
          ) : error ? (
            <ErrorState message="Failed to load workflow details" />
          ) : !pack ? null : (
            <>
              {activeTab === "overview" && <OverviewTab pack={pack} />}
              {activeTab === "designer" && (
                <div className="text-center py-16 text-gray-400">
                  <Edit className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm font-medium text-gray-500">Workflow Designer</p>
                  <p className="text-xs text-gray-400 mt-1">Open the full workspace to edit stages and transitions.</p>
                  <button
                    onClick={() => onOpenDesigner?.(packId)}
                    className="mt-4 inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md bg-navy-600 text-white hover:bg-navy-700"
                  >
                    <ExternalLink className="w-3 h-3" /> Open Designer
                  </button>
                </div>
              )}
              {activeTab === "rules" && (
                <div className="text-center py-16 text-gray-400">
                  <Brain className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm font-medium text-gray-500">Rule Builder</p>
                  <p className="text-xs text-gray-400 mt-1">Configure routing rules and conditions.</p>
                </div>
              )}
              {activeTab === "simulator" && (
                <div className="text-center py-16 text-gray-400">
                  <Play className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm font-medium text-gray-500">Simulator</p>
                  <p className="text-xs text-gray-400 mt-1">Test workflow routing with sample data.</p>
                </div>
              )}
              {activeTab === "versions" && <VersionsTab packId={packId} versions={versions ?? []} />}
              {activeTab === "analytics" && <AnalyticsTab packId={packId} />}
              {activeTab === "timeline" && (
                <div className="text-center py-16 text-gray-400">
                  <Activity className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm font-medium text-gray-500">Activity Timeline</p>
                  <p className="text-xs text-gray-400 mt-1">Workflow activity will appear here after execution.</p>
                </div>
              )}
              {activeTab === "history" && (
                <div className="text-center py-16 text-gray-400">
                  <History className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm font-medium text-gray-500">Change History</p>
                  <p className="text-xs text-gray-400 mt-1">Audit log for all changes to this workflow.</p>
                </div>
              )}
              {activeTab === "settings" && (
                <div className="text-center py-16 text-gray-400">
                  <Settings className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm font-medium text-gray-500">Workflow Settings</p>
                  <p className="text-xs text-gray-400 mt-1">Configure notifications, SLA defaults, and escalation rules.</p>
                </div>
              )}
            </>
          )}
        </div>
      </motion.div>
    </>
  );
}

function OverviewTab({ pack }: { pack: NonNullable<ReturnType<typeof useWorkflowPack>["data"]> }) {
  const healthScore = pack.health_score ?? 0;
  const healthLabel = healthScore >= 90 ? "Healthy" : healthScore >= 70 ? "Warning" : "Critical";
  const healthColor = healthScore >= 90 ? "text-emerald-600" : healthScore >= 70 ? "text-amber-600" : "text-red-600";
  const healthBg = healthScore >= 90 ? "bg-emerald-50 border-emerald-200" : healthScore >= 70 ? "bg-amber-50 border-amber-200" : "bg-red-50 border-red-200";

  return (
    <div className="space-y-5">
      {/* Health Card — clickable */}
      <button className={`w-full rounded-xl border p-4 text-left ${healthBg} hover:shadow-sm transition-shadow`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Shield className={`w-5 h-5 ${healthColor}`} />
            <span className="text-sm font-semibold text-gray-900">Workflow Health</span>
          </div>
          <span className="text-[10px] text-gray-400">Click for details →</span>
        </div>
        <div className="flex items-end gap-3">
          <div>
            <span className={`text-2xl font-bold ${healthColor}`}>{healthScore}</span>
            <span className="text-xs text-gray-400 ml-0.5">/ 100</span>
          </div>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            healthScore >= 90 ? "bg-emerald-100 text-emerald-700" :
            healthScore >= 70 ? "bg-amber-100 text-amber-700" :
            "bg-red-100 text-red-700"
          }`}>{healthLabel}</span>
        </div>
        {pack.warning_count > 0 && (
          <div className="flex items-center gap-1 mt-2 text-[11px] text-amber-600">
            <AlertTriangle className="w-3 h-3" />
            {pack.warning_count} issue{pack.warning_count !== 1 ? "s" : ""} to resolve
          </div>
        )}
        {pack.warning_count === 0 && healthScore >= 90 && (
          <p className="text-[11px] text-emerald-600 mt-1">✓ No blocking issues</p>
        )}
      </button>

      {/* Info Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <InfoCard label="Status" value={<StatusBadge variant="primary" status={pack.status} />} />
        <InfoCard label="Version" value={`v${pack.version}`} />
        <InfoCard label="Owner" value={pack.owner || "—"} />
        <InfoCard label="Category" value={pack.category} />
        <InfoCard label="Created" value={pack.created_at ? formatDate(pack.created_at) : "—"} />
        <InfoCard label="Published" value={pack.last_published ? formatDate(pack.last_published) : "Not published"} />
        <InfoCard label="Industry" value={pack.industry || "—"} />
        <InfoCard label="Region" value={pack.region || "—"} />
      </div>

      {/* Usage Stats */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Usage</h3>
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Running" value={pack.running_instances ?? 0} />
          <MetricCard label="Completed" value={pack.usage_count ?? 0} />
          <MetricCard label="Stages" value={pack.stages?.length ?? 0} />
          <MetricCard label="Templates" value={pack.templates_using ?? 0} />
        </div>
      </div>

      {/* Stages Preview */}
      {pack.stages && pack.stages.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Stages</h3>
          <div className="flex items-center gap-1.5 flex-wrap">
            {pack.stages.map((stage, i) => (
              <React.Fragment key={stage.name}>
                <span className="px-2.5 py-1 bg-gray-100 rounded-md text-[11px] text-gray-700 font-medium border border-gray-200">
                  {stage.name}
                </span>
                {i < pack.stages.length - 1 && (
                  <span className="text-gray-300 text-xs">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Dependencies */}
      {pack.templates_using > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Dependencies</h3>
          <div className="rounded-xl border border-gray-200 divide-y divide-gray-100">
            <div className="flex justify-between px-4 py-2.5 text-[11px]">
              <span className="text-gray-500">Templates using this workflow</span>
              <span className="font-medium text-gray-900">{pack.templates_using}</span>
            </div>
            <div className="flex justify-between px-4 py-2.5 text-[11px]">
              <span className="text-gray-500">Contracts currently running</span>
              <span className="font-medium text-gray-900">{pack.contracts_running}</span>
            </div>
            <div className="flex justify-between px-4 py-2.5 text-[11px]">
              <span className="text-gray-500">Referenced rules</span>
              <span className="font-medium text-gray-900">{pack.referenced_rule_count}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function VersionsTab({ packId, versions }: { packId: string; versions: NonNullable<ReturnType<typeof useVersions>["data"]> }) {
  return (
    <div className="space-y-3">
      {versions.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <GitCompare className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No versions yet</p>
          <p className="text-xs text-gray-400 mt-1">Save the workflow to create version 1.</p>
        </div>
      ) : (
        versions.map((v) => (
          <div key={v.version_id} className="rounded-xl border border-gray-200 bg-white p-4 hover:shadow-sm transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">v{v.version_number}</span>
                <StatusBadge variant="secondary" status={v.status} />
                <span className="text-[11px] text-gray-400">Score: {v.health_score}%</span>
              </div>
              <div className="flex gap-1.5">
                {v.status !== "published" && (
                  <button className="text-[10px] font-medium px-2.5 py-1 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition-colors">
                    Publish
                  </button>
                )}
                <button className="text-[10px] font-medium px-2.5 py-1 rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors">
                  Compare
                </button>
              </div>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-gray-500">
              <span>{v.stage_count} stages</span>
              <span>{v.rule_count} rules</span>
              {v.published_by && <span>by {v.published_by}</span>}
              {v.published_at && <span>{formatDate(v.published_at)}</span>}
            </div>
            {v.change_summary && (
              <p className="mt-2 text-[11px] text-gray-400 italic border-t border-gray-100 pt-2">{v.change_summary}</p>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function AnalyticsTab({ packId }: { packId: string }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "Total Executions", value: "—" },
          { label: "Avg Approval Time", value: "—" },
          { label: "Approval Rate", value: "—" },
          { label: "SLA Breaches", value: "—" },
          { label: "Rejection Rate", value: "—" },
          { label: "Bottleneck Stage", value: "—" },
        ].map((m) => (
          <div key={m.label} className="rounded-xl border border-gray-200 bg-white p-4 text-center">
            <div className="text-xl font-bold text-gray-300">{m.value}</div>
            <div className="text-[10px] text-gray-500 mt-1">{m.label}</div>
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-gray-200 p-6 text-center">
        <BarChart3 className="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p className="text-sm font-medium text-gray-500">No execution data yet</p>
        <p className="text-xs text-gray-400 mt-1">Publish and execute this workflow to begin collecting analytics.</p>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2.5">
      <div className="text-[10px] text-gray-500 mb-0.5">{label}</div>
      <div className="text-[12px] font-medium text-gray-900">{value}</div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 text-center shadow-sm">
      <div className="text-lg font-bold text-navy-900">{value}</div>
      <div className="text-[10px] text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

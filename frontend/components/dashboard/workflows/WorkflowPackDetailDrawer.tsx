"use client";

import React, { useState } from "react";
import {
  X, Workflow, Edit, Play, CheckCircle, Clock, AlertTriangle,
  FileJson, Download, Copy, Archive, BarChart3, GitCompare,
  Layers, Users, FileText, Activity, TrendingUp,
} from "lucide-react";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { useWorkflowPack, useVersions } from "@/services/hooks/useWorkflowAdmin";

interface Props {
  packId: string;
  onClose: () => void;
  onOpenDesigner?: (packId: string) => void;
}

export function WorkflowPackDetailDrawer({ packId, onClose, onOpenDesigner }: Props) {
  const [activeTab, setActiveTab] = useState<"overview" | "versions" | "analytics" | "timeline">("overview");
  const { data: pack, isLoading, error } = useWorkflowPack(packId);
  const { data: versions } = useVersions(packId);

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Drawer */}
      <div className="relative ml-auto w-full max-w-2xl bg-navy-900 border-l border-navy-700 shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-navy-900 border-b border-navy-700">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <Workflow className="w-5 h-5 text-gold-400" />
              <div>
                <h2 className="text-lg font-semibold text-gray-100">
                  {isLoading ? "Loading..." : pack?.name ?? "Workflow Pack"}
                </h2>
                {pack && (
                  <span className="text-sm text-gray-400">v{pack.version} · {pack.category}</span>
                )}
              </div>
            </div>
            <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-200 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Quick Actions */}
          {pack && (
            <div className="flex gap-2 px-4 pb-4">
              <ActionButton
                icon={<Edit className="w-4 h-4" />}
                label="Designer"
                onClick={() => onOpenDesigner?.(packId)}
              />
              <ActionButton icon={<Play className="w-4 h-4" />} label="Simulator" />
              <ActionButton icon={<CheckCircle className="w-4 h-4" />} label="Validate" />
              <ActionButton icon={<Layers className="w-4 h-4" />} label="Publish" />
              <ActionButton icon={<Copy className="w-4 h-4" />} label="Clone" />
              <ActionButton icon={<Download className="w-4 h-4" />} label="Export" />
            </div>
          )}

          {/* Tabs */}
          <div className="flex border-b border-navy-700 px-4">
            {([
              { id: "overview", label: "Overview", icon: FileText },
              { id: "versions", label: "Versions", icon: GitCompare },
              { id: "analytics", label: "Analytics", icon: BarChart3 },
              { id: "timeline", label: "Timeline", icon: Activity },
            ] as const).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-gold-500 text-gold-400"
                    : "border-transparent text-gray-400 hover:text-gray-200"
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
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
              {activeTab === "versions" && <VersionsTab packId={packId} versions={versions ?? []} />}
              {activeTab === "analytics" && <AnalyticsTab packId={packId} />}
              {activeTab === "timeline" && <TimelineTab />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ActionButton({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-navy-800 text-gray-300 rounded-lg hover:bg-navy-700 hover:text-gold-400 transition-colors"
    >
      {icon}
      {label}
    </button>
  );
}

function OverviewTab({ pack }: { pack: NonNullable<ReturnType<typeof useWorkflowPack>["data"]> }) {
  const healthColor = pack.health_score >= 90 ? "text-green-400" : pack.health_score >= 70 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="space-y-6">
      {/* Health Card */}
      <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <span className={`text-2xl font-bold ${healthColor}`}>{pack.health_score}%</span>
          <span className="text-sm text-gray-300">Workflow Health</span>
          {pack.warning_count > 0 && (
            <span className="flex items-center gap-1 text-yellow-400 text-sm">
              <AlertTriangle className="w-4 h-4" />
              {pack.warning_count} warning{pack.warning_count !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          <span className="text-gray-400">✅ Validation: {pack.health_score}</span>
          <span className="text-gray-400">📋 {pack.templates_using} templates</span>
          <span className="text-gray-400">🔗 {pack.contracts_running} running contracts</span>
          {pack.warning_count === 0 && <span className="text-green-400">No blocking issues</span>}
        </div>
      </div>

      {/* Overview Info */}
      <div className="grid grid-cols-2 gap-4">
        <InfoCard label="Status" value={pack.status} />
        <InfoCard label="Version" value={`v${pack.version}`} />
        <InfoCard label="Owner" value={pack.owner} />
        <InfoCard label="Category" value={pack.category} />
        <InfoCard label="Created" value={formatDate(pack.created_at)} />
        <InfoCard label="Published" value={pack.last_published ? formatDate(pack.last_published) : "Not published"} />
        <InfoCard label="Industry" value={pack.industry ?? "—"} />
        <InfoCard label="Region" value={pack.region ?? "—"} />
      </div>

      {/* Usage */}
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-3">Usage</h3>
        <div className="grid grid-cols-4 gap-3">
          <MetricCard label="Running" value={pack.running_instances} />
          <MetricCard label="Completed" value={pack.usage_count} />
          <MetricCard label="Templates" value={pack.templates_using} />
          <MetricCard label="Contracts" value={pack.contracts_running} />
        </div>
      </div>

      {/* Dependencies */}
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-3">Dependencies</h3>
        <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Templates using this workflow</span>
            <span className="text-gray-200">{pack.templates_using}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Contracts currently running</span>
            <span className="text-gray-200">{pack.contracts_running}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Contract types</span>
            <span className="text-gray-200">{pack.contract_types?.join(", ") ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Default for template</span>
            <span className="text-gray-200">{pack.default_for_template ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Referenced rules</span>
            <span className="text-gray-200">{pack.referenced_rule_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Referenced actions</span>
            <span className="text-gray-200">{pack.referenced_action_count}</span>
          </div>
        </div>
      </div>

      {/* Stages Preview */}
      {pack.stages && pack.stages.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Stages</h3>
          <div className="flex items-center gap-2 flex-wrap">
            {pack.stages.map((stage, i) => (
              <React.Fragment key={stage.name}>
                <span className="px-3 py-1.5 bg-navy-800 rounded-lg text-sm text-gray-300 border border-navy-700">
                  {stage.name}
                </span>
                {i < pack.stages.length - 1 && (
                  <span className="text-gray-600">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function VersionsTab({ packId, versions }: { packId: string; versions: NonNullable<ReturnType<typeof useVersions>["data"]> }) {
  return (
    <div className="space-y-4">
      {versions.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No versions yet</div>
      ) : (
        versions.map((v) => (
          <div key={v.version_id} className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-100">v{v.version_number}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  v.status === "published" ? "bg-green-500/20 text-green-400" :
                  v.status === "draft" ? "bg-yellow-500/20 text-yellow-400" :
                  "bg-gray-500/20 text-gray-400"
                }`}>
                  {v.status}
                </span>
                <span className="text-sm text-gray-500">Score: {v.health_score}%</span>
              </div>
              <div className="flex gap-2">
                {v.status !== "published" && (
                  <button className="text-xs px-3 py-1 bg-gold-500/20 text-gold-400 rounded-lg hover:bg-gold-500/30">
                    Publish
                  </button>
                )}
                <button className="text-xs px-3 py-1 bg-navy-700 text-gray-300 rounded-lg hover:bg-navy-600">
                  Compare
                </button>
              </div>
            </div>
            <div className="flex gap-4 text-sm text-gray-500">
              <span>{v.stage_count} stages</span>
              <span>{v.rule_count} rules</span>
              {v.published_by && <span>by {v.published_by}</span>}
              {v.published_at && <span>{formatDate(v.published_at)}</span>}
            </div>
            {v.change_summary && (
              <div className="mt-2 text-sm text-gray-400 italic">{v.change_summary}</div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function AnalyticsTab({ packId }: { packId: string }) {
  return (
    <div className="space-y-6">
      {/* Metrics grid showing what will be tracked */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
          <div className="text-2xl font-bold text-gray-400">—</div>
          <div className="text-xs text-gray-500 mt-1">Total Executions</div>
        </div>
        <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
          <div className="text-2xl font-bold text-gray-400">—</div>
          <div className="text-xs text-gray-500 mt-1">Avg Approval Time</div>
        </div>
        <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
          <div className="text-2xl font-bold text-gray-400">—</div>
          <div className="text-xs text-gray-500 mt-1">Approval Rate</div>
        </div>
        <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
          <div className="text-2xl font-bold text-gray-400">—</div>
          <div className="text-xs text-gray-500 mt-1">SLA Breaches</div>
        </div>
        <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
          <div className="text-2xl font-bold text-gray-400">—</div>
          <div className="text-xs text-gray-500 mt-1">Rejection Rate</div>
        </div>
        <div className="p-4 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
          <div className="text-2xl font-bold text-gray-400">—</div>
          <div className="text-xs text-gray-500 mt-1">Bottleneck Stage</div>
        </div>
      </div>

      {/* Trend chart placeholder */}
      <div className="p-6 bg-navy-800/50 border border-navy-700 rounded-xl text-center">
        <div className="flex items-center justify-center gap-2 mb-3">
          <TrendingUp className="w-5 h-5 text-gray-600" />
          <span className="text-sm font-medium text-gray-500">Execution Trends</span>
        </div>
        <div className="h-32 flex items-center justify-center border border-dashed border-navy-600 rounded-lg">
          <BarChart3 className="w-8 h-8 text-gray-700" />
        </div>
      </div>

      {/* Empty state */}
      <div className="text-center py-6 border border-dashed border-navy-700 rounded-xl">
        <BarChart3 className="w-10 h-10 mx-auto mb-2 text-gray-600" />
        <p className="text-sm text-gray-400">No execution data yet</p>
        <p className="text-xs text-gray-500 mt-1">Publish and execute this workflow to begin collecting analytics.</p>
      </div>
    </div>
  );
}

function TimelineTab() {
  return (
    <div className="text-center py-12 text-gray-500">
      <Activity className="w-12 h-12 mx-auto mb-3 text-gray-600" />
      <p>Workflow activity timeline will be displayed here</p>
      <p className="text-sm">View the full lifecycle: create, publish, archive, simulate, validate</p>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 bg-navy-800/50 border border-navy-700 rounded-lg">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-sm text-gray-200 capitalize">{value}</div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-3 bg-navy-800/50 border border-navy-700 rounded-lg text-center">
      <div className="text-xl font-bold text-gray-100">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

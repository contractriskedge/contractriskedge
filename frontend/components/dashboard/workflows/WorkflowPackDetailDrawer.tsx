"use client";

import React, { useState, useMemo, useCallback } from "react";
import {
  Workflow, Edit, Play, CheckCircle, Clock, AlertTriangle,
  FileJson, Download, Copy, BarChart3, GitCompare,
  Layers, FileText, Activity, Settings, History, Brain,
  Save, ChevronRight, XCircle, Info,
} from "lucide-react";
import { DetailDrawer, DrawerTabBtn, DrawerBreadcrumbs } from "@/components/shared/DetailDrawer";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import {
  useWorkflowPack,
  useVersions,
  useValidation,
  usePackAnalytics,
  useCreateVersion,
  usePublishVersion,
} from "@/services/hooks/useWorkflowAdmin";
import type { WorkflowPackDetail, WorkflowVersionSummary } from "@/services/api/workflowAdmin";
import { WorkflowDesigner } from "./WorkflowDesigner";
import { RuleBuilder } from "./RuleBuilder";
import { WorkflowSimulator } from "./WorkflowSimulator";
import {
  buildHealthDetails,
  getHealthColors,
  getHealthLabel,
  issueSeverityClass,
} from "./workflowHealthUtils";

export type WorkflowPackTabId =
  | "overview"
  | "designer"
  | "rules"
  | "simulator"
  | "versions"
  | "analytics"
  | "timeline"
  | "history"
  | "settings";

interface TabDef {
  id: WorkflowPackTabId;
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

const TAB_LABELS: Record<WorkflowPackTabId, string> = Object.fromEntries(
  TABS.map((t) => [t.id, t.label]),
) as Record<WorkflowPackTabId, string>;

interface Props {
  packId: string;
  onClose: () => void;
  initialTab?: WorkflowPackTabId;
}

export function WorkflowPackDetailDrawer({ packId, onClose, initialTab = "overview" }: Props) {
  const [activeTab, setActiveTab] = useState<WorkflowPackTabId>(initialTab);
  const [healthExpanded, setHealthExpanded] = useState(false);
  const [validateRequested, setValidateRequested] = useState(false);
  const [draftSaved, setDraftSaved] = useState(false);

  const { data: pack, isLoading, error, refetch } = useWorkflowPack(packId);
  const { data: versions } = useVersions(packId);
  const createVersion = useCreateVersion(packId);
  const publishVersion = usePublishVersion(packId);

  const latestVersion = useMemo(() => {
    if (!versions?.length) return null;
    return versions.reduce((best, v) =>
      v.version_number > best.version_number ? v : best,
    versions[0]);
  }, [versions]);

  const { data: validation, isLoading: validating, refetch: runValidation } = useValidation(
    packId,
    latestVersion?.version_id ?? "",
  );

  const { data: analytics, isLoading: analyticsLoading } = usePackAnalytics(packId);

  const healthDetails = useMemo(() => {
    if (!pack) return null;
    return buildHealthDetails(
      pack.health_score ?? 0,
      pack.warning_count ?? 0,
      validateRequested ? validation : null,
    );
  }, [pack, validation, validateRequested]);

  const handleSaveDraft = useCallback(async () => {
    if (!pack) return;
    try {
      await createVersion.mutateAsync({
        stages: pack.stages ?? [],
        rules: pack.rules ?? [],
        change_summary: "Draft saved from workflow editor",
      });
      setDraftSaved(true);
      setTimeout(() => setDraftSaved(false), 3000);
      refetch();
    } catch {
      // mutation error surfaced via react-query
    }
  }, [pack, createVersion, refetch]);

  const handleValidate = useCallback(async () => {
    setValidateRequested(true);
    setHealthExpanded(true);
    await runValidation();
  }, [runValidation]);

  const handleSimulate = useCallback(() => {
    setActiveTab("simulator");
  }, []);

  const handlePublish = useCallback(async () => {
    if (!latestVersion || latestVersion.status === "published") {
      setActiveTab("versions");
      return;
    }
    if (healthDetails && !healthDetails.canPublish) {
      setValidateRequested(true);
      setHealthExpanded(true);
      await runValidation();
      return;
    }
    try {
      await publishVersion.mutateAsync({ versionId: latestVersion.version_id });
      refetch();
    } catch {
      setActiveTab("versions");
    }
  }, [latestVersion, healthDetails, publishVersion, refetch, runValidation]);

  const stickyActions = pack ? (
    <>
      <button
        onClick={handleSaveDraft}
        disabled={createVersion.isPending}
        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50"
      >
        <Save className="w-3 h-3" />
        {createVersion.isPending ? "Saving…" : draftSaved ? "Saved" : "Save Draft"}
      </button>
      <button
        onClick={handleValidate}
        disabled={validating || !latestVersion}
        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
      >
        <CheckCircle className="w-3 h-3" />
        {validating ? "Validating…" : "Validate"}
      </button>
      <button
        onClick={handleSimulate}
        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
      >
        <Play className="w-3 h-3" /> Simulate
      </button>
      <button
        onClick={handlePublish}
        disabled={publishVersion.isPending || !latestVersion}
        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm disabled:opacity-50"
      >
        <Layers className="w-3 h-3" />
        {publishVersion.isPending ? "Publishing…" : "Publish"}
      </button>
    </>
  ) : null;

  return (
    <DetailDrawer
      open={!!packId}
      onClose={onClose}
      size="xl"
      breadcrumbs={
        <DrawerBreadcrumbs
          items={[
            { label: "Workflow Administration", onClick: onClose },
            { label: pack?.name ?? "Loading…" },
            { label: pack ? `v${pack.version}` : "—" },
            { label: TAB_LABELS[activeTab] },
          ]}
        />
      }
      icon={
        <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center">
          <Workflow className="w-4 h-4 text-white" />
        </div>
      }
      title={isLoading ? "Loading…" : pack?.name ?? "Workflow Pack"}
      subtitle={
        pack
          ? `${pack.category} · ${pack.owner || "—"} · ${pack.status}`
          : undefined
      }
      headerActions={
        pack ? <StatusBadge variant="primary" status={pack.status} /> : undefined
      }
      stickyActions={stickyActions}
      tabs={
        <>
          {TABS.map((tab) => (
            <DrawerTabBtn
              key={tab.id}
              label={tab.label}
              icon={<tab.icon className="w-3 h-3" />}
              active={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
            />
          ))}
        </>
      }
    >
      {isLoading ? (
        <div className="space-y-4">
          <LoadingSkeleton className="h-24 rounded-lg" />
          <LoadingSkeleton className="h-48 rounded-lg" />
          <LoadingSkeleton className="h-32 rounded-lg" />
        </div>
      ) : error ? (
        <ErrorState message="Failed to load workflow details" onRetry={() => refetch()} />
      ) : !pack ? null : (
        <TabContent
          tab={activeTab}
          pack={pack}
          packId={packId}
          versions={versions ?? []}
          latestVersion={latestVersion}
          analytics={analytics}
          analyticsLoading={analyticsLoading}
          healthDetails={healthDetails}
          healthExpanded={healthExpanded}
          onHealthToggle={() => setHealthExpanded((v) => !v)}
          onValidate={handleValidate}
          validating={validating}
          onPublish={handlePublish}
          publishPending={publishVersion.isPending}
        />
      )}
    </DetailDrawer>
  );
}

// ── Tab Content Router ─────────────────────────────────────────────

function TabContent({
  tab,
  pack,
  packId,
  versions,
  latestVersion,
  analytics,
  analyticsLoading,
  healthDetails,
  healthExpanded,
  onHealthToggle,
  onValidate,
  validating,
  onPublish,
  publishPending,
}: {
  tab: WorkflowPackTabId;
  pack: WorkflowPackDetail;
  packId: string;
  versions: WorkflowVersionSummary[];
  latestVersion: WorkflowVersionSummary | null;
  analytics: ReturnType<typeof usePackAnalytics>["data"];
  analyticsLoading: boolean;
  healthDetails: ReturnType<typeof buildHealthDetails> | null;
  healthExpanded: boolean;
  onHealthToggle: () => void;
  onValidate: () => void;
  validating: boolean;
  onPublish: () => void;
  publishPending: boolean;
}) {
  switch (tab) {
    case "overview":
      return (
        <OverviewTab
          pack={pack}
          healthDetails={healthDetails}
          healthExpanded={healthExpanded}
          onHealthToggle={onHealthToggle}
          onValidate={onValidate}
          validating={validating}
        />
      );
    case "designer":
      return (
        <div className="-m-5 p-0 h-[calc(100vh-14rem)] min-h-[480px]">
          <WorkflowDesigner
            embedded
            initialStages={pack.stages}
            onSave={() => {}}
            onBack={() => {}}
          />
        </div>
      );
    case "rules":
      return (
        <div className="-m-5 p-0 h-[calc(100vh-14rem)] min-h-[480px]">
          <RuleBuilder embedded onSave={() => {}} onBack={() => {}} />
        </div>
      );
    case "simulator":
      return (
        <div className="-m-5 p-0">
          <WorkflowSimulator
            embedded
            packId={packId}
            versionId={latestVersion?.version_id}
            onBack={() => {}}
          />
        </div>
      );
    case "versions":
      return (
        <VersionsTab
          versions={versions}
          onPublish={onPublish}
          publishPending={publishPending}
        />
      );
    case "analytics":
      return (
        <AnalyticsTab
          pack={pack}
          analytics={analytics}
          isLoading={analyticsLoading}
        />
      );
    case "timeline":
      return <TimelineTab pack={pack} />;
    case "history":
      return <HistoryTab pack={pack} versions={versions} />;
    case "settings":
      return <SettingsTab pack={pack} />;
    default:
      return null;
  }
}

// ── Overview ───────────────────────────────────────────────────────

function OverviewTab({
  pack,
  healthDetails,
  healthExpanded,
  onHealthToggle,
  onValidate,
  validating,
}: {
  pack: WorkflowPackDetail;
  healthDetails: ReturnType<typeof buildHealthDetails> | null;
  healthExpanded: boolean;
  onHealthToggle: () => void;
  onValidate: () => void;
  validating: boolean;
}) {
  const score = healthDetails?.score ?? pack.health_score ?? 0;
  const colors = getHealthColors(score);

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <button
          onClick={onHealthToggle}
          className={`w-full p-4 text-left border-b ${colors.bg} hover:shadow-sm transition-shadow`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <CheckCircle className={`w-5 h-5 ${colors.text}`} />
              <span className="text-sm font-semibold text-gray-900">Workflow Health</span>
            </div>
            <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
              {healthExpanded ? "Hide details" : "View details"}
              <ChevronRight className={`w-3 h-3 transition-transform ${healthExpanded ? "rotate-90" : ""}`} />
            </span>
          </div>
          <div className="flex items-end gap-3">
            <div>
              <span className={`text-2xl font-bold ${colors.text}`}>{score}</span>
              <span className="text-xs text-gray-400 ml-0.5">/ 100</span>
            </div>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${colors.badge}`}>
              {getHealthLabel(colors.tier)}
            </span>
          </div>
          {pack.warning_count > 0 && (
            <div className="flex items-center gap-1 mt-2 text-[11px] text-amber-600">
              <AlertTriangle className="w-3 h-3" />
              {pack.warning_count} issue{pack.warning_count !== 1 ? "s" : ""} to resolve
            </div>
          )}
          {pack.warning_count === 0 && score >= 90 && (
            <p className="text-[11px] text-emerald-600 mt-1">No blocking issues</p>
          )}
        </button>

        {healthExpanded && healthDetails && (
          <div className="p-4 space-y-4 bg-white">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Health Details</h4>
              <button
                onClick={onValidate}
                disabled={validating}
                className="text-[10px] font-medium text-navy-600 hover:text-navy-800 disabled:opacity-50"
              >
                {validating ? "Running validation…" : "Re-run validation"}
              </button>
            </div>

            <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-[11px] text-gray-600">
              <Info className="w-3 h-3 inline mr-1 text-gray-400" />
              {healthDetails.calculation}
            </div>

            {healthDetails.publishBlockers.length > 0 && (
              <HealthIssueSection
                title="Publish Blockers"
                issues={healthDetails.publishBlockers}
                icon={<XCircle className="w-3.5 h-3.5 text-red-500" />}
              />
            )}

            {healthDetails.validationIssues.length > 0 && (
              <HealthIssueSection
                title="Validation Issues"
                issues={healthDetails.validationIssues}
                icon={<AlertTriangle className="w-3.5 h-3.5 text-red-500" />}
              />
            )}

            {healthDetails.warnings.length > 0 && (
              <HealthIssueSection
                title="Warnings"
                issues={healthDetails.warnings}
                icon={<AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
              />
            )}

            {healthDetails.recommendations.length > 0 && (
              <div>
                <h5 className="text-[11px] font-semibold text-gray-500 mb-2">Recommendations</h5>
                <ul className="space-y-1.5">
                  {healthDetails.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 text-[11px] text-gray-600">
                      <ChevronRight className="w-3 h-3 text-navy-500 mt-0.5 flex-shrink-0" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {healthDetails.publishBlockers.length === 0 &&
              healthDetails.validationIssues.length === 0 &&
              healthDetails.warnings.length === 0 &&
              pack.warning_count === 0 && (
              <p className="text-[11px] text-gray-500">No validation issues detected. Run Validate for a full check.</p>
            )}
          </div>
        )}
      </div>

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

      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Usage</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard label="Running" value={pack.running_instances ?? 0} />
          <MetricCard label="Completed" value={pack.usage_count ?? 0} />
          <MetricCard label="Stages" value={pack.stages?.length ?? 0} />
          <MetricCard label="Templates" value={pack.templates_using ?? 0} />
        </div>
      </div>

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

      {(pack.templates_using > 0 || pack.contracts_running > 0) && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Dependencies</h3>
          <div className="rounded-xl border border-gray-200 divide-y divide-gray-100">
            <DependencyRow label="Templates using this workflow" value={pack.templates_using} />
            <DependencyRow label="Contracts currently running" value={pack.contracts_running} />
            <DependencyRow label="Referenced rules" value={pack.referenced_rule_count} />
          </div>
        </div>
      )}
    </div>
  );
}

function HealthIssueSection({
  title,
  issues,
  icon,
}: {
  title: string;
  issues: { severity: string; message: string; stage: string | null; suggestion: string }[];
  icon: React.ReactNode;
}) {
  return (
    <div>
      <h5 className="text-[11px] font-semibold text-gray-500 mb-2 flex items-center gap-1.5">
        {icon} {title}
      </h5>
      <div className="space-y-1.5">
        {issues.map((issue, i) => (
          <div
            key={i}
            className={`rounded-lg border px-3 py-2 text-[11px] ${issueSeverityClass(issue.severity as "error" | "warning")}`}
          >
            <p className="font-medium">{issue.message}</p>
            {issue.stage && <p className="text-gray-500 mt-0.5">Stage: {issue.stage}</p>}
            {issue.suggestion && <p className="text-gray-500 mt-0.5 italic">{issue.suggestion}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Versions ───────────────────────────────────────────────────────

function VersionsTab({
  versions,
  onPublish,
  publishPending,
}: {
  versions: WorkflowVersionSummary[];
  onPublish: () => void;
  publishPending: boolean;
}) {
  if (versions.length === 0) {
    return (
      <EmptyState
        icon={<GitCompare className="w-10 h-10 text-gray-300" />}
        title="No versions yet"
        message="Save a draft to create version 1 of this workflow pack."
      />
    );
  }

  return (
    <div className="space-y-3">
      {versions.map((v) => (
        <div key={v.version_id} className="rounded-xl border border-gray-200 bg-white p-5 hover:shadow-sm transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-gray-900">v{v.version_number}</span>
              <StatusBadge variant="secondary" status={v.status} />
              <span className="text-[11px] text-gray-400">Health: {v.health_score}%</span>
            </div>
            <div className="flex gap-1.5">
              {v.status !== "published" && (
                <button
                  onClick={onPublish}
                  disabled={publishPending}
                  className="text-[10px] font-medium px-2.5 py-1 rounded-md bg-navy-700 text-white hover:bg-navy-800 transition-colors disabled:opacity-50"
                >
                  Publish
                </button>
              )}
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
      ))}
    </div>
  );
}

// ── Analytics ──────────────────────────────────────────────────────

function AnalyticsTab({
  pack,
  analytics,
  isLoading,
}: {
  pack: WorkflowPackDetail;
  analytics: ReturnType<typeof usePackAnalytics>["data"];
  isLoading: boolean;
}) {
  if (isLoading) {
    return <LoadingSkeleton className="h-48 rounded-lg" />;
  }

  const hasData = analytics && (analytics.completed_instances > 0 || analytics.running_instances > 0);

  if (!hasData) {
    return (
      <EmptyState
        icon={<BarChart3 className="w-10 h-10 text-gray-300" />}
        title="No execution data yet"
        message={`Publish and run "${pack.name}" on contracts to begin collecting analytics.`}
      />
    );
  }

  const metrics = [
    { label: "Total Executions", value: String(analytics!.completed_instances + analytics!.running_instances) },
    { label: "Avg Completion", value: `${analytics!.avg_completion_hours.toFixed(1)}h` },
    { label: "Avg Approval", value: `${analytics!.avg_approval_hours.toFixed(1)}h` },
    { label: "SLA Breach Rate", value: `${(analytics!.sla_breach_rate * 100).toFixed(1)}%` },
    { label: "Rejection Rate", value: `${(analytics!.rejected_rate * 100).toFixed(1)}%` },
    { label: "Running Now", value: String(analytics!.running_instances) },
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-xl border border-gray-200 bg-white p-4 text-center shadow-sm">
            <div className="text-xl font-bold text-navy-900">{m.value}</div>
            <div className="text-[10px] text-gray-500 mt-1">{m.label}</div>
          </div>
        ))}
      </div>
      {analytics!.trend_data?.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Recent Trend</h3>
          <div className="rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-gray-500">
                  <th className="text-left px-4 py-2 font-medium">Date</th>
                  <th className="text-right px-4 py-2 font-medium">Completed</th>
                  <th className="text-right px-4 py-2 font-medium">Avg Hours</th>
                </tr>
              </thead>
              <tbody>
                {analytics!.trend_data.slice(-7).map((row) => (
                  <tr key={row.date} className="border-b border-gray-100 last:border-0">
                    <td className="px-4 py-2 text-gray-700">{formatDate(row.date)}</td>
                    <td className="px-4 py-2 text-right text-gray-700 tabular-nums">{row.completed}</td>
                    <td className="px-4 py-2 text-right text-gray-700 tabular-nums">{row.avg_hours.toFixed(1)}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Timeline ───────────────────────────────────────────────────────

function TimelineTab({ pack }: { pack: WorkflowPackDetail }) {
  if ((pack.running_instances ?? 0) === 0 && (pack.usage_count ?? 0) === 0) {
    return (
      <EmptyState
        icon={<Activity className="w-10 h-10 text-gray-300" />}
        title="No workflow activity yet"
        message="Instance timelines will appear here once contracts begin executing this workflow."
      />
    );
  }

  const events = [
    pack.last_published && {
      label: "Last published",
      detail: `Version ${pack.version} published`,
      date: pack.last_published,
      status: "completed" as const,
    },
    pack.created_at && {
      label: "Pack created",
      detail: `${pack.name} workflow pack created`,
      date: pack.created_at,
      status: "completed" as const,
    },
  ].filter(Boolean) as { label: string; detail: string; date: string; status: "completed" | "running" }[];

  return (
    <div className="space-y-4">
      <p className="text-[11px] text-gray-500">
        {pack.running_instances} running · {pack.usage_count} completed
      </p>
      <div className="relative pl-6 space-y-4">
        {events.map((event, i) => (
          <div key={i} className="relative">
            <div className="absolute -left-6 top-1 w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-white" />
            {i < events.length - 1 && (
              <div className="absolute -left-[1.125rem] top-4 bottom-0 w-0.5 bg-gray-200" />
            )}
            <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900">{event.label}</span>
                <span className="text-[10px] text-gray-400">{formatDate(event.date)}</span>
              </div>
              <p className="text-[11px] text-gray-500 mt-0.5">{event.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── History ────────────────────────────────────────────────────────

function HistoryTab({
  pack,
  versions,
}: {
  pack: WorkflowPackDetail;
  versions: WorkflowVersionSummary[];
}) {
  const entries = [
    ...versions.map((v) => ({
      id: v.version_id,
      action: v.status === "published" ? "Published" : "Version saved",
      detail: `v${v.version_number}${v.change_summary ? ` — ${v.change_summary}` : ""}`,
      actor: v.published_by ?? pack.owner ?? "—",
      date: v.published_at ?? v.created_at,
    })),
  ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<History className="w-10 h-10 text-gray-300" />}
        title="No change history"
        message="Version saves and publishes will be recorded here."
      />
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200 text-gray-500">
            <th className="text-left px-4 py-2.5 font-medium">Date</th>
            <th className="text-left px-4 py-2.5 font-medium">Action</th>
            <th className="text-left px-4 py-2.5 font-medium">Details</th>
            <th className="text-left px-4 py-2.5 font-medium">Actor</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50">
              <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">{formatDate(entry.date)}</td>
              <td className="px-4 py-2.5 font-medium text-gray-900">{entry.action}</td>
              <td className="px-4 py-2.5 text-gray-600">{entry.detail}</td>
              <td className="px-4 py-2.5 text-gray-500">{entry.actor}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Settings ───────────────────────────────────────────────────────

function SettingsTab({ pack }: { pack: WorkflowPackDetail }) {
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Pack Configuration</h3>
        <div className="rounded-xl border border-gray-200 divide-y divide-gray-100">
          <SettingsRow label="Pack ID" value={pack.pack_id} mono />
          <SettingsRow label="Default for template" value={pack.default_for_template || "None"} />
          <SettingsRow label="Jurisdiction" value={pack.jurisdiction || "—"} />
          <SettingsRow label="Contract types" value={pack.contract_types?.join(", ") || "—"} />
          <SettingsRow label="Referenced actions" value={String(pack.referenced_action_count)} />
          <SettingsRow label="Built-in pack" value={pack.is_built_in ? "Yes" : "No"} />
        </div>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Quick Actions</h3>
        <div className="flex flex-wrap gap-2">
          <button className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <Copy className="w-3 h-3" /> Clone Pack
          </button>
          <button className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <Download className="w-3 h-3" /> Export
          </button>
          <button className="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <FileJson className="w-3 h-3" /> Import
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Shared UI helpers ──────────────────────────────────────────────

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

function DependencyRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between px-4 py-2.5 text-[11px]">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}

function SettingsRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between px-4 py-2.5 text-[11px]">
      <span className="text-gray-500">{label}</span>
      <span className={`font-medium text-gray-900 text-right max-w-[60%] truncate ${mono ? "font-mono text-[10px]" : ""}`}>
        {value}
      </span>
    </div>
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

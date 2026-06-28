/**
 * OperationsCenter — Enterprise Operations & Observability Dashboard.
 *
 * Provides 9 tabs:
 *   Health    — System Health Dashboard with per-service status
 *   Metrics   — Prometheus metrics overview
 *   Logs      — Structured log viewer with filtering
 *   Queues    — Background job queue monitoring
 *   Errors    — Error categorization and trends
 *   Integrations — External integration health
 *   Scheduler — Scheduled task monitoring
 *   Alerts    — Active alert evaluation
 *
 * Also includes: Support Bundle download, Slow Operations dashboard.
 */

"use client";

import React, { useState, useCallback, useMemo } from "react";
import {
  Activity,
  BarChart3,
  FileText,
  ListChecks,
  AlertTriangle,
  Plug,
  Calendar,
  Bell,
  Download,
  Shield,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Loader2,
  RefreshCw,
  Database,
  Server,
  Cpu,
  Search,
  Mail,
  HardDrive,
  Brain,
  Users,
  Gauge,
  ChevronRight,
  ExternalLink,
  Wifi,
  WifiOff,
  Zap,
  Layers,
  TrendingUp,
  PieChart,
  Terminal,
  Filter,
  Copy,
  ChevronDown,
  Eye,
  EyeOff,
} from "lucide-react";

import {
  useSystemHealth,
  useQueueStatus,
  useSchedulerStatus,
  useIntegrationHealth,
  useErrorDashboard,
  useSlowOperations,
  useAlerts,
  useSupportBundle,
} from "@/services/hooks/useOperations";

// ── Types ──────────────────────────────────────────────────────────

type TabId = "health" | "metrics" | "logs" | "queues" | "errors" | "integrations" | "scheduler" | "alerts";

interface Tab {
  id: TabId;
  label: string;
  icon: React.ElementType;
}

const TABS: Tab[] = [
  { id: "health", label: "Health", icon: Activity },
  { id: "metrics", label: "Metrics", icon: BarChart3 },
  { id: "logs", label: "Logs", icon: FileText },
  { id: "queues", label: "Queues", icon: ListChecks },
  { id: "errors", label: "Errors", icon: AlertTriangle },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "scheduler", label: "Scheduler", icon: Calendar },
  { id: "alerts", label: "Alerts", icon: Bell },
];

// ── Helpers ────────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status) {
    case "healthy": return "text-emerald-500";
    case "warning":
    case "degraded": return "text-amber-500";
    case "failed":
    case "critical": return "text-red-500";
    default: return "text-gray-400";
  }
}

function statusBgColor(status: string): string {
  switch (status) {
    case "healthy": return "bg-emerald-50 border-emerald-200 dark:bg-emerald-900/10 dark:border-emerald-800";
    case "warning":
    case "degraded": return "bg-amber-50 border-amber-200 dark:bg-amber-900/10 dark:border-amber-800";
    case "failed":
    case "critical": return "bg-red-50 border-red-200 dark:bg-red-900/10 dark:border-red-800";
    default: return "bg-gray-50 border-gray-200 dark:bg-gray-800 dark:border-gray-700";
  }
}

function statusIcon(status: string, className = "w-4 h-4") {
  switch (status) {
    case "healthy": return <CheckCircle2 className={`${className} text-emerald-500`} />;
    case "warning":
    case "degraded": return <AlertCircle className={`${className} text-amber-500`} />;
    case "failed":
    case "critical": return <XCircle className={`${className} text-red-500`} />;
    default: return <Loader2 className={`${className} text-gray-400 animate-spin`} />;
  }
}

function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${ms.toFixed(1)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
}

// ── Tab Components ─────────────────────────────────────────────────

function HealthTab() {
  const { data: health, isLoading, error, refetch } = useSystemHealth(15_000);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-navy-400" />
        <span className="ml-2 text-navy-500">Loading health data...</span>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="text-center py-20">
        <XCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <p className="text-gray-500">Unable to load system health</p>
        <button onClick={() => refetch()} className="mt-3 text-sm text-blue-500 hover:underline">
          Retry
        </button>
      </div>
    );
  }

  const services = Object.entries(health.services || {});

  return (
    <div className="space-y-6">
      {/* Overall Status Banner */}
      <div className={`rounded-xl border p-5 ${statusBgColor(health.status)}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {health.status === "healthy" ? (
              <Shield className="w-8 h-8 text-emerald-500" />
            ) : health.status === "warning" ? (
              <AlertTriangle className="w-8 h-8 text-amber-500" />
            ) : (
              <XCircle className="w-8 h-8 text-red-500" />
            )}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                {health.status}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {health.healthy_count} of {health.total_count} services healthy
              </p>
            </div>
          </div>
          <div className="text-right text-sm text-gray-500 dark:text-gray-400">
            <p>Uptime: {formatUptime(health.uptime_seconds)}</p>
            <p className="text-xs text-gray-400">v{health.version} · {health.environment}</p>
          </div>
        </div>
      </div>

      {/* Service Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {services.map(([name, svc]) => (
          <div
            key={name}
            className={`rounded-lg border p-4 ${statusBgColor(svc.status)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {statusIcon(svc.status, "w-5 h-5")}
                <span className="font-medium text-sm text-gray-900 dark:text-white capitalize">
                  {name.replace(/_/g, " ")}
                </span>
              </div>
              <span className={`text-xs font-medium capitalize ${statusColor(svc.status)}`}>
                {svc.status}
              </span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
              {svc.response_time_ms != null && (
                <p>Response: {formatDuration(svc.response_time_ms)}</p>
              )}
              {svc.detail && <p className="truncate" title={svc.detail}>{svc.detail}</p>}
              {svc.error && <p className="text-red-400 truncate" title={svc.error}>Error: {svc.error}</p>}
              {svc.last_checked && (
                <p className="text-gray-400">Checked: {new Date(svc.last_checked).toLocaleTimeString()}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Metrics Tab ────────────────────────────────────────────────────

function MetricsTab() {
  const { data: health } = useSystemHealth();

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="API Requests" value="—" subtitle="Tracked via /metrics" icon={Server} />
        <MetricCard title="Active Workers" value={health?.services?.workers?.status === "healthy" ? "Online" : "Offline"} subtitle="Celery workers" icon={Cpu} />
        <MetricCard title="Database" value={health?.services?.database?.status === "healthy" ? "Connected" : "Disconnected"} subtitle="PostgreSQL" icon={Database} />
        <MetricCard title="Cache" value={health?.services?.redis?.status === "healthy" ? "Connected" : "Disconnected"} subtitle="Redis" icon={Layers} />
      </div>

      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Prometheus Metrics Endpoint</h3>
        <div className="bg-gray-50 dark:bg-navy-900 rounded-lg p-4 font-mono text-xs">
          <p className="text-gray-500 mb-2"># Available metrics (scrape /metrics for full data)</p>
          <p className="text-gray-700 dark:text-gray-300">http_requests_total — Total HTTP requests by method, endpoint, status</p>
          <p className="text-gray-700 dark:text-gray-300">http_request_duration_seconds — Request latency histogram</p>
          <p className="text-gray-700 dark:text-gray-300">http_requests_in_flight — Current in-flight requests</p>
          <p className="text-gray-700 dark:text-gray-300">workflow_instances_started_total — Workflows started</p>
          <p className="text-gray-700 dark:text-gray-300">workflow_instances_completed_total — Workflows completed</p>
          <p className="text-gray-700 dark:text-gray-300">workflow_duration_seconds — Workflow duration</p>
          <p className="text-gray-700 dark:text-gray-300">ai_analysis_total — AI analysis runs</p>
          <p className="text-gray-700 dark:text-gray-300">ai_token_usage_total — Token consumption</p>
          <p className="text-gray-700 dark:text-gray-300">search_queries_total — Search queries by strategy</p>
          <p className="text-gray-700 dark:text-gray-300">search_duration_seconds — Search latency</p>
          <p className="text-gray-700 dark:text-gray-300">queue_depth — Queue depth by name</p>
          <p className="text-gray-700 dark:text-gray-300">db_pool_stats — Connection pool statistics</p>
        </div>
        <p className="text-xs text-gray-400 mt-3">
          Endpoint: <code className="bg-gray-100 dark:bg-navy-900 px-1.5 py-0.5 rounded">GET /metrics</code>
          — Configure Prometheus to scrape this endpoint.
        </p>
      </div>
    </div>
  );
}

function MetricCard({ title, value, subtitle, icon: Icon }: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ElementType;
}) {
  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-navy-50 dark:bg-navy-700 rounded-lg">
          <Icon className="w-5 h-5 text-navy-500 dark:text-navy-300" />
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-white">{value}</p>
          <p className="text-[10px] text-gray-400">{subtitle}</p>
        </div>
      </div>
    </div>
  );
}

// ── Logs Tab ───────────────────────────────────────────────────────

function LogsTab() {
  const [filter, setFilter] = useState("");
  const [showRaw, setShowRaw] = useState(false);

  // Sample structured log entries (in production these come from the backend)
  const sampleLogs = [
    { timestamp: "2026-06-28T10:23:45Z", severity: "INFO", module: "http.api", action: "POST /api/v1/reviews/", outcome: "success", duration_ms: 234, tenant_id: "t1", correlation_id: "cid-001", user_id: "u1", request_id: "req-001", message: "Request completed" },
    { timestamp: "2026-06-28T10:23:44Z", severity: "WARNING", module: "ai.analysis", action: "analyze", outcome: "retry", duration_ms: 5120, tenant_id: "t1", correlation_id: "cid-002", user_id: "u2", request_id: "req-002", message: "AI analysis rate limited, retrying" },
    { timestamp: "2026-06-28T10:23:40Z", severity: "ERROR", module: "workflow.engine", action: "transition", outcome: "error", duration_ms: 150, tenant_id: "t2", correlation_id: "cid-003", user_id: "u3", request_id: "req-003", message: "Workflow transition failed: invalid state" },
  ];

  const filteredLogs = filter
    ? sampleLogs.filter(l =>
        Object.values(l).some(v => String(v).toLowerCase().includes(filter.toLowerCase()))
      )
    : sampleLogs;

  return (
    <div className="space-y-4">
      {/* Filter Bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by any field..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-800 text-gray-900 dark:text-white"
          />
        </div>
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700"
        >
          {showRaw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          {showRaw ? "Formatted" : "Raw JSON"}
        </button>
      </div>

      {/* Log Table */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 dark:bg-navy-900 border-b border-gray-200 dark:border-navy-700">
                <th className="text-left px-3 py-2 font-medium text-gray-500">Timestamp</th>
                <th className="text-left px-3 py-2 font-medium text-gray-500">Severity</th>
                <th className="text-left px-3 py-2 font-medium text-gray-500">Module</th>
                <th className="text-left px-3 py-2 font-medium text-gray-500">Action</th>
                <th className="text-left px-3 py-2 font-medium text-gray-500">Outcome</th>
                <th className="text-right px-3 py-2 font-medium text-gray-500">Duration</th>
                <th className="text-left px-3 py-2 font-medium text-gray-500">Correlation ID</th>
                <th className="text-left px-3 py-2 font-medium text-gray-500">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
              {filteredLogs.map((log, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-navy-700/50">
                  <td className="px-3 py-2 text-gray-500 whitespace-nowrap font-mono">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      log.severity === "ERROR" ? "bg-red-100 text-red-700" :
                      log.severity === "WARNING" ? "bg-amber-100 text-amber-700" :
                      "bg-emerald-100 text-emerald-700"
                    }`}>
                      {log.severity}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-300 font-mono">{log.module}</td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{log.action}</td>
                  <td className="px-3 py-2">
                    <span className={`${log.outcome === "success" ? "text-emerald-500" : log.outcome === "error" ? "text-red-500" : "text-amber-500"}`}>
                      {log.outcome}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-gray-500 font-mono">{formatDuration(log.duration_ms)}</td>
                  <td className="px-3 py-2 text-gray-500 font-mono text-[10px]">{log.correlation_id}</td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{log.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredLogs.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            No log entries match your filter
          </div>
        )}
      </div>

      {showRaw && (
        <pre className="bg-gray-50 dark:bg-navy-900 rounded-lg p-4 text-xs font-mono overflow-x-auto">
          {JSON.stringify(filteredLogs, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ── Queues Tab ─────────────────────────────────────────────────────

function QueuesTab() {
  const { data: queueStatus, isLoading, error } = useQueueStatus(15_000);
  const { data: scheduler } = useSchedulerStatus(30_000);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-navy-400" />
      </div>
    );
  }

  const queueEntries = queueStatus?.queues ? Object.entries(queueStatus.queues) : [];

  return (
    <div className="space-y-6">
      {/* Queue Depths */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-5">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Queue Depths</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {queueEntries.map(([name, depth]) => (
            <div key={name} className="text-center p-3 bg-gray-50 dark:bg-navy-900 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 capitalize mb-1">{name}</p>
              <p className={`text-2xl font-bold ${
                depth > 100 ? "text-red-500" : depth > 20 ? "text-amber-500" : "text-emerald-500"
              }`}>
                {depth < 0 ? "—" : depth}
              </p>
            </div>
          ))}
        </div>
        {queueStatus && (
          <div className="mt-4 flex items-center gap-4 text-xs text-gray-500">
            <span>Total pending: <strong>{queueStatus.total_pending}</strong></span>
            <span>Dead letter: <strong className={queueStatus.dead_letter_count > 0 ? "text-red-500" : ""}>
              {queueStatus.dead_letter_count}
            </strong></span>
            <span>Backlog: <strong className={queueStatus.has_backlog ? "text-red-500" : "text-emerald-500"}>
              {queueStatus.has_backlog ? "Yes" : "No"}
            </strong></span>
          </div>
        )}
      </div>

      {/* Active Tasks */}
      {scheduler && scheduler.active_tasks && scheduler.active_tasks.length > 0 && (
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-5">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Active Tasks</h3>
          <div className="space-y-2">
            {scheduler.active_tasks.map((task, i) => (
              <div key={i} className="flex items-center gap-3 text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-navy-900 rounded-lg p-2">
                <Cpu className="w-3.5 h-3.5 text-blue-500" />
                <span className="font-medium">{task.task_name}</span>
                <span className="text-gray-400">on {task.worker}</span>
                <span className="text-gray-400 ml-auto">
                  Started: {task.started ? new Date(task.started * 1000).toLocaleTimeString() : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {(!queueStatus || queueEntries.length === 0) && !error && (
        <div className="text-center py-10 text-gray-400">
          <Layers className="w-10 h-10 mx-auto mb-2 opacity-50" />
          <p>No queue data available</p>
        </div>
      )}

      {error && (
        <div className="text-center py-10 text-red-400">
          <p>Failed to load queue status</p>
        </div>
      )}
    </div>
  );
}

// ── Errors Tab ─────────────────────────────────────────────────────

function ErrorsTab() {
  const { data: errors, isLoading } = useErrorDashboard(60_000);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-navy-400" />
      </div>
    );
  }

  const categories = errors?.categories || {};
  const trends = errors?.trends || {};
  const categoryEntries = Object.entries(categories).sort((a, b) => Number(b[1]) - Number(a[1]));
  const totalErrors = categoryEntries.reduce((sum, [, count]) => sum + Number(count), 0);

  return (
    <div className="space-y-6">
      {/* Trends */}
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(trends).map(([period, data]) => (
          <div key={period} className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{data.label}</p>
            <p className={`text-2xl font-bold ${
              Number(data.count) > 50 ? "text-red-500" : Number(data.count) > 10 ? "text-amber-500" : "text-emerald-500"
            }`}>
              {data.count}
            </p>
            <p className="text-[10px] text-gray-400 mt-1">errors</p>
          </div>
        ))}
      </div>

      {/* Categories */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-5">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Error Categories</h3>
        {categoryEntries.length > 0 ? (
          <div className="space-y-3">
            {categoryEntries.map(([category, count]) => {
              const pct = totalErrors > 0 ? (Number(count) / totalErrors) * 100 : 0;
              return (
                <div key={category} className="flex items-center gap-3">
                  <span className="text-xs text-gray-600 dark:text-gray-400 w-28 capitalize">{category}</span>
                  <div className="flex-1 bg-gray-100 dark:bg-navy-900 rounded-full h-2">
                    <div
                      className="bg-navy-500 rounded-full h-2 transition-all"
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-12 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-6 text-gray-400">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-400" />
            <p>No errors recorded in the selected period</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Integrations Tab ───────────────────────────────────────────────

function IntegrationsTab() {
  const { data: integrations, isLoading } = useIntegrationHealth(60_000);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-navy-400" />
      </div>
    );
  }

  if (!integrations || integrations.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400">
        <Plug className="w-10 h-10 mx-auto mb-2 opacity-50" />
        <p>No integration data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {integrations.map((int) => (
        <div
          key={int.name}
          className={`rounded-lg border p-4 ${statusBgColor(int.status)}`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {statusIcon(int.status, "w-5 h-5")}
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                  {int.name.replace(/_/g, " ")}
                </h4>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {int.detail || (int.status === "healthy" ? "Operational" : int.error || "Unknown")}
                </p>
              </div>
            </div>
            <div className="text-right text-xs text-gray-500 dark:text-gray-400">
              {int.response_time_ms != null && (
                <p>{formatDuration(int.response_time_ms)}</p>
              )}
              {int.last_checked && (
                <p className="text-[10px] text-gray-400">
                  {new Date(int.last_checked).toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Scheduler Tab ──────────────────────────────────────────────────

function SchedulerTab() {
  const { data: scheduler, isLoading } = useSchedulerStatus(30_000);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-navy-400" />
      </div>
    );
  }

  const scheduled = scheduler?.scheduled_tasks || [];
  const active = scheduler?.active_tasks || [];

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Scheduled</p>
          <p className="text-2xl font-bold text-navy-600 dark:text-navy-200">{scheduler?.total_scheduled || 0}</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Active</p>
          <p className="text-2xl font-bold text-blue-500">{scheduler?.total_active || 0}</p>
        </div>
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Status</p>
          <p className={`text-lg font-bold capitalize ${statusColor(scheduler?.status || "unknown")}`}>
            {scheduler?.status || "Unknown"}
          </p>
        </div>
      </div>

      {/* Scheduled Tasks */}
      {scheduled.length > 0 && (
        <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-5">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Scheduled Tasks</h3>
          <div className="space-y-2">
            {scheduled.map((task, i) => (
              <div key={i} className="flex items-center gap-3 text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-navy-900 rounded-lg p-2">
                <Calendar className="w-3.5 h-3.5 text-navy-400" />
                <span className="font-medium">{task.task_name}</span>
                <span className="text-gray-400">on {task.worker}</span>
                <span className="text-gray-400 ml-auto">
                  ETA: {task.eta ? new Date(task.eta).toLocaleString() : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {scheduled.length === 0 && active.length === 0 && (
        <div className="text-center py-10 text-gray-400">
          <Calendar className="w-10 h-10 mx-auto mb-2 opacity-50" />
          <p>No scheduler data available</p>
        </div>
      )}
    </div>
  );
}

// ── Alerts Tab ─────────────────────────────────────────────────────

function AlertsTab() {
  const { data: alerts, isLoading, refetch } = useAlerts(30_000);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-navy-400" />
      </div>
    );
  }

  if (!alerts || alerts.length === 0) {
    return (
      <div className="text-center py-16">
        <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">All Clear</h3>
        <p className="text-sm text-gray-500 mt-1">No active alerts</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">{alerts.length} active alert(s)</p>
        <button onClick={() => refetch()} className="text-xs text-blue-500 hover:underline flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`rounded-lg border-l-4 p-4 ${
            alert.severity === "critical"
              ? "border-l-red-500 bg-red-50 dark:bg-red-900/10"
              : alert.severity === "warning"
              ? "border-l-amber-500 bg-amber-50 dark:bg-amber-900/10"
              : "border-l-blue-500 bg-blue-50 dark:bg-blue-900/10"
          }`}
        >
          <div className="flex items-start gap-3">
            {alert.severity === "critical" ? (
              <XCircle className="w-5 h-5 text-red-500 mt-0.5" />
            ) : alert.severity === "warning" ? (
              <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
            ) : (
              <Bell className="w-5 h-5 text-blue-500 mt-0.5" />
            )}
            <div className="flex-1">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white">{alert.title}</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{alert.description}</p>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
                <span className="capitalize">{alert.severity}</span>
                <span>Source: {alert.source}</span>
                <span>{new Date(alert.timestamp).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Slow Operations Panel ──────────────────────────────────────────

function SlowOperationsPanel() {
  const { data: slow, isLoading } = useSlowOperations(60_000);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-navy-400" />
      </div>
    );
  }

  const sections: { key: keyof typeof slow; label: string; icon: React.ElementType }[] = [
    { key: "apis", label: "Slow APIs", icon: Server },
    { key: "queries", label: "Slow Queries", icon: Database },
    { key: "workflows", label: "Slow Workflows", icon: Activity },
    { key: "searches", label: "Slow Searches", icon: Search },
  ];

  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-5">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Slow Operations (Top 20)</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.map(({ key, label, icon: Icon }) => {
          const items = slow?.[key] as Array<Record<string, unknown>> | undefined;
          return (
            <div key={key}>
              <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1.5">
                <Icon className="w-3.5 h-3.5" />
                {label}
              </h4>
              {items && items.length > 0 ? (
                <div className="space-y-1">
                  {items.slice(0, 5).map((item, i) => (
                    <div key={i} className="text-[10px] text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-navy-900 rounded px-2 py-1 truncate">
                      {item.method && <span className="font-mono text-gray-400">{item.method as string} </span>}
                      {item.path && <span>{item.path as string}</span>}
                      {item.duration_ms != null && (
                        <span className="text-amber-500 ml-1">{formatDuration(item.duration_ms as number)}</span>
                      )}
                      {item.duration_seconds != null && (
                        <span className="text-amber-500 ml-1">{(item.duration_seconds as number).toFixed(0)}s</span>
                      )}
                      {item.status && <span className="text-gray-400 ml-1">({item.status as string})</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400 italic">No data</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────

export function OperationsCenter() {
  const [activeTab, setActiveTab] = useState<TabId>("health");
  const supportBundle = useSupportBundle();

  const handleDownloadBundle = useCallback(async () => {
    try {
      const blob = await supportBundle.mutateAsync();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `support-bundle-${new Date().toISOString().split("T")[0]}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Support bundle download failed:", err);
    }
  }, [supportBundle]);

  const renderTab = () => {
    switch (activeTab) {
      case "health": return <HealthTab />;
      case "metrics": return <MetricsTab />;
      case "logs": return <LogsTab />;
      case "queues": return <QueuesTab />;
      case "errors": return <ErrorsTab />;
      case "integrations": return <IntegrationsTab />;
      case "scheduler": return <SchedulerTab />;
      case "alerts": return <AlertsTab />;
      default: return <HealthTab />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy-900 dark:text-white">Operations Center</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            System observability, health monitoring, and diagnostics
          </p>
        </div>
        <button
          onClick={handleDownloadBundle}
          disabled={supportBundle.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-navy-900 text-white rounded-lg hover:bg-navy-800 disabled:opacity-50 text-sm font-medium transition-colors"
        >
          {supportBundle.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          Generate Support Bundle
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-navy-700">
        <nav className="flex space-x-1 overflow-x-auto">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? "border-navy-900 text-navy-900 dark:border-gold-400 dark:text-gold-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {renderTab()}
      </div>

      {/* Slow Operations Section (always visible below tabs) */}
      <SlowOperationsPanel />
    </div>
  );
}

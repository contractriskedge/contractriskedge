/**
 * ExecutiveAlertCenter — Alert timeline and management panel.
 *
 * Displays operational alerts with severity coding, filtering,
 * acknowledgement, escalation, and drilldown capabilities.
 */

"use client";

import React, { useState, useMemo } from "react";
import { AlertTriangle, CheckCircle, ArrowUpCircle, Eye, Filter, X, Loader2, RefreshCw } from "lucide-react";
import { useAlertCenter, ALERT_TYPE_CONFIG, SEVERITY_ORDER, type AlertSeverity, type AlertType, type AlertStatus } from "@/src/lib/alerts/alertCenter";

const SEVERITY_BG: Record<AlertSeverity, string> = {
  critical: "bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800",
  high: "bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800",
  medium: "bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800",
  low: "bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800",
};

const SEVERITY_DOT: Record<AlertSeverity, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-blue-500",
};

const SEVERITY_TEXT: Record<AlertSeverity, string> = {
  critical: "text-red-700 dark:text-red-300",
  high: "text-orange-700 dark:text-orange-300",
  medium: "text-yellow-700 dark:text-yellow-300",
  low: "text-blue-700 dark:text-blue-300",
};

const STATUS_BADGE: Record<AlertStatus, { bg: string; text: string; label: string }> = {
  open: { bg: "bg-red-50", text: "text-red-700", label: "Open" },
  acknowledged: { bg: "bg-yellow-50", text: "text-yellow-700", label: "Acknowledged" },
  resolved: { bg: "bg-green-50", text: "text-green-700", label: "Resolved" },
  escalated: { bg: "bg-orange-50", text: "text-orange-700", label: "Escalated" },
};

export function ExecutiveAlertCenter() {
  const {
    alerts,
    totalAlerts,
    openCount,
    criticalCount,
    selectedAlert,
    setSelectedAlert,
    filter,
    setFilter,
    acknowledgeAlert,
    resolveAlert,
    escalateAlert,
    isLoading,
    error,
    refetch,
  } = useAlertCenter();

  const [showFilters, setShowFilters] = useState(false);

  // Summary counts by severity
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const s of SEVERITY_ORDER) counts[s] = 0;
    for (const a of alerts) counts[a.severity]++;
    return counts;
  }, [alerts]);

  if (isLoading && alerts.length === 0) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="w-5 h-5 text-gold-400 animate-spin" />
      </div>
    );
  }

  if (error && alerts.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-xs text-gray-400">
        <span>Failed to load alerts. </span>
        <button onClick={() => refetch()} className="text-gold-600 hover:text-gold-700 underline ml-1">Retry</button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* ── Summary Bar ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-navy-900 dark:text-white">
            {totalAlerts} alert{totalAlerts !== 1 ? "s" : ""}
          </span>
          {criticalCount > 0 && (
            <span className="text-xs font-semibold text-red-600 bg-red-50 dark:bg-red-900/20 px-2 py-0.5 rounded-full">
              {criticalCount} critical
            </span>
          )}
          {openCount > 0 && (
            <span className="text-xs font-medium text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-2 py-0.5 rounded-full">
              {openCount} open
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-1.5 rounded text-xs ${showFilters ? "bg-gray-200 dark:bg-navy-600" : "hover:bg-gray-100 dark:hover:bg-navy-700"} text-gray-500`}
            title="Filter alerts"
          >
            <Filter className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => refetch()} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500" title="Refresh">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ── Severity Counts ── */}
      <div className="flex gap-1.5">
        {SEVERITY_ORDER.map((sev) => (
          <button
            key={sev}
            onClick={() => setFilter((f) => ({ ...f, severity: f.severity === sev ? undefined : sev }))}
            className={`flex-1 py-1.5 rounded-lg text-center text-[10px] font-medium border transition-all ${
              filter.severity === sev
                ? `${SEVERITY_BG[sev]} border-current`
                : "bg-gray-50 dark:bg-navy-700 border-transparent text-gray-500"
            }`}
          >
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${SEVERITY_DOT[sev]} mr-1`} />
            {sev}: {severityCounts[sev]}
          </button>
        ))}
      </div>

      {/* ── Filter Bar ── */}
      {showFilters && (
        <div className="flex flex-wrap gap-2 p-2 bg-gray-50 dark:bg-navy-700 rounded-lg">
          <select
            value={filter.type ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, type: (e.target.value || undefined) as AlertType }))}
            className="text-[10px] px-2 py-1 rounded border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-800"
          >
            <option value="">All types</option>
            {Object.entries(ALERT_TYPE_CONFIG).map(([key, cfg]) => (
              <option key={key} value={key}>{cfg.label}</option>
            ))}
          </select>
          <select
            value={filter.status ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, status: (e.target.value || undefined) as AlertStatus }))}
            className="text-[10px] px-2 py-1 rounded border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-800"
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
            <option value="escalated">Escalated</option>
          </select>
        </div>
      )}

      {/* ── Alert List ── */}
      <div className="space-y-1.5 max-h-96 overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-xs text-gray-400">
            <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-400" />
            No alerts match current filters
          </div>
        ) : (
          alerts.map((alert) => {
            const typeCfg = ALERT_TYPE_CONFIG[alert.type];
            return (
              <div
                key={alert.id}
                className={`p-2.5 rounded-lg border cursor-pointer transition-all hover:shadow-sm ${
                  selectedAlert?.id === alert.id ? "ring-2 ring-gold-400" : ""
                } ${SEVERITY_BG[alert.severity]}`}
                onClick={() => setSelectedAlert(selectedAlert?.id === alert.id ? null : alert)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 min-w-0">
                    <span className="text-base flex-shrink-0 mt-0.5">{typeCfg?.icon ?? "🔔"}</span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-xs font-semibold ${SEVERITY_TEXT[alert.severity]}`}>
                          {typeCfg?.label ?? alert.type}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${STATUS_BADGE[alert.status].bg} ${STATUS_BADGE[alert.status].text}`}>
                          {STATUS_BADGE[alert.status].label}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-navy-900 dark:text-white mt-0.5">{alert.title}</p>
                      <p className="text-[10px] text-gray-500 mt-0.5 line-clamp-2">{alert.description}</p>
                      {alert.affected_count && alert.affected_count > 0 && (
                        <p className="text-[10px] text-gray-400 mt-0.5">{alert.affected_count} affected</p>
                      )}
                    </div>
                  </div>
                  <span className="text-[10px] text-gray-400 flex-shrink-0 whitespace-nowrap">
                    {formatTimestamp(alert.timestamp)}
                  </span>
                </div>

                {/* ── Action Buttons ── */}
                {alert.status === "open" && (
                  <div className="flex items-center gap-1.5 mt-2 ml-6">
                    <button
                      onClick={(e) => { e.stopPropagation(); acknowledgeAlert(alert.id); }}
                      className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 hover:bg-gray-50 dark:hover:bg-navy-600 text-gray-600"
                    >
                      <Eye className="w-3 h-3" /> Acknowledge
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); escalateAlert(alert.id); }}
                      className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 hover:bg-orange-50 dark:hover:bg-navy-600 text-orange-600"
                    >
                      <ArrowUpCircle className="w-3 h-3" /> Escalate
                    </button>
                  </div>
                )}
                {alert.status === "acknowledged" && (
                  <div className="flex items-center gap-1.5 mt-2 ml-6">
                    <button
                      onClick={(e) => { e.stopPropagation(); resolveAlert(alert.id); }}
                      className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-white dark:bg-navy-700 border border-gray-200 dark:border-navy-600 hover:bg-green-50 dark:hover:bg-navy-600 text-green-600"
                    >
                      <CheckCircle className="w-3 h-3" /> Resolve
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    const now = Date.now();
    const diff = now - date.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  } catch {
    return ts;
  }
}

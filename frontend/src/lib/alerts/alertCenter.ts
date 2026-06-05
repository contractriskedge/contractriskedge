/**
 * Executive alert center — operational alert types and state management.
 *
 * Alert types:
 * - SLA breach
 * - reviewer overload
 * - vendor concentration spike
 * - workflow bottleneck
 * - abnormal AI drift
 * - ingestion backlog
 * - provider instability
 * - compliance escalation
 * - suspicious tenant activity
 * - replay inconsistency
 */

"use client";

import { useState, useCallback, useMemo } from "react";
import { useExecutiveAnomalies } from "@/src/lib/executive/executiveQueries";
import { useInvalidationOrchestrator } from "@/src/lib/realtime/invalidationOrchestrator";

// ── Alert Types ───────────────────────────────────────────────────

export type AlertType =
  | "sla_breach"
  | "reviewer_overload"
  | "vendor_concentration_spike"
  | "workflow_bottleneck"
  | "ai_drift"
  | "ingestion_backlog"
  | "provider_instability"
  | "compliance_escalation"
  | "suspicious_activity"
  | "replay_inconsistency";

export type AlertSeverity = "critical" | "high" | "medium" | "low";

export type AlertStatus = "open" | "acknowledged" | "resolved" | "escalated";

export interface ExecutiveAlert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  description: string;
  timestamp: string;
  correlation_id?: string;
  affected_entities?: string[];
  affected_count?: number;
  recommendation?: string;
  actionable: boolean;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  metadata?: Record<string, unknown>;
}

// ── Alert Configuration ───────────────────────────────────────────

export const ALERT_TYPE_CONFIG: Record<AlertType, { icon: string; label: string; defaultSeverity: AlertSeverity }> = {
  sla_breach: { icon: "🚨", label: "SLA Breach", defaultSeverity: "critical" },
  reviewer_overload: { icon: "⚠️", label: "Reviewer Overload", defaultSeverity: "high" },
  vendor_concentration_spike: { icon: "📊", label: "Vendor Concentration", defaultSeverity: "high" },
  workflow_bottleneck: { icon: "🔴", label: "Workflow Bottleneck", defaultSeverity: "medium" },
  ai_drift: { icon: "🤖", label: "AI Drift", defaultSeverity: "medium" },
  ingestion_backlog: { icon: "📥", label: "Ingestion Backlog", defaultSeverity: "medium" },
  provider_instability: { icon: "🔌", label: "Provider Instability", defaultSeverity: "high" },
  compliance_escalation: { icon: "⚖️", label: "Compliance Escalation", defaultSeverity: "critical" },
  suspicious_activity: { icon: "🔍", label: "Suspicious Activity", defaultSeverity: "high" },
  replay_inconsistency: { icon: "🔄", label: "Replay Inconsistency", defaultSeverity: "medium" },
};

export const SEVERITY_ORDER: AlertSeverity[] = ["critical", "high", "medium", "low"];

// ── Hook ──────────────────────────────────────────────────────────

export function useAlertCenter() {
  const [alerts, setAlerts] = useState<ExecutiveAlert[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<ExecutiveAlert | null>(null);
  const [filter, setFilter] = useState<{ severity?: AlertSeverity; type?: AlertType; status?: AlertStatus }>({});
  const { invalidate } = useInvalidationOrchestrator();

  // Fetch anomalies from backend
  const { data: anomaliesData, isLoading, error, refetch } = useExecutiveAnomalies(24);

  // Merge backend anomalies into alert state
  useMemo(() => {
    if (!anomaliesData) return;

    // Transform backend anomaly response to ExecutiveAlert[]
    const backendAlerts: ExecutiveAlert[] = [];
    const raw = anomaliesData as any;

    if (raw.anomalies && Array.isArray(raw.anomalies)) {
      for (const a of raw.anomalies) {
        // Build evidence string from before/after window comparison
        const evidenceParts: string[] = [];
        if (a.current_value !== undefined && a.expected_value !== undefined) {
          evidenceParts.push(`before: ${a.expected_value}, after: ${a.current_value}`);
        }
        if (a.deviation_pct !== undefined) {
          evidenceParts.push(`change: ${a.deviation_pct > 0 ? '+' : ''}${a.deviation_pct.toFixed(1)}%`);
        }
        const evidence = evidenceParts.length > 0 ? ` (${evidenceParts.join(' | ')})` : '';

        backendAlerts.push({
          id: a.anomaly_id ?? a.id ?? `alert-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          type: mapAnomalyType(a.category ?? a.type),
          severity: a.severity ?? "medium",
          status: a.acknowledged ? "acknowledged" : "open",
          title: a.title ?? a.type ?? "Operational Alert",
          description: (a.description ?? a.message ?? "") + evidence,
          timestamp: a.detected_at ?? a.timestamp ?? a.created_at ?? new Date().toISOString(),
          correlation_id: a.correlation_id,
          affected_entities: a.affected_entities ?? a.affected_reviews ?? [],
          affected_count: a.affected_count ?? a.affected_reviews?.length ?? 0,
          recommendation: a.recommendation,
          actionable: true,
          metadata: a,
        });
      }
    }

    setAlerts((prev) => {
      // Merge: new alerts take precedence, preserve acknowledged state
      const existingMap = new Map(prev.map((a) => [a.id, a]));

      // Track seen anomaly signatures to deduplicate (same title + metric_name = same anomaly)
      const seenSignatures = new Set<string>();
      for (const a of prev) {
        const meta = a.metadata as Record<string, unknown> | undefined;
        const sig = `${a.title}::${meta?.metric_name ?? ''}`;
        if (sig) seenSignatures.add(sig);
      }

      for (const alert of backendAlerts) {
        // Deduplicate by anomaly signature (title + metric_name)
        const meta = alert.metadata as Record<string, unknown> | undefined;
        const sig = `${alert.title}::${meta?.metric_name ?? ''}`;
        if (sig && seenSignatures.has(sig)) {
          // Update existing alert's timestamp and values instead of adding duplicate
          const existing = existingMap.get(alert.id);
          if (existing) {
            existingMap.set(alert.id, { ...alert, status: existing.status });
          }
          continue;
        }
        if (sig) seenSignatures.add(sig);

        const existing = existingMap.get(alert.id);
        if (existing && existing.status === "acknowledged") {
          alert.status = "acknowledged";
          alert.acknowledged_at = existing.acknowledged_at;
          alert.acknowledged_by = existing.acknowledged_by;
        }
        existingMap.set(alert.id, alert);
      }
      return Array.from(existingMap.values());
    });
  }, [anomaliesData]);

  // Filtered alerts
  const filteredAlerts = useMemo(() => {
    let result = [...alerts];

    if (filter.severity) {
      result = result.filter((a) => a.severity === filter.severity);
    }
    if (filter.type) {
      result = result.filter((a) => a.type === filter.type);
    }
    if (filter.status) {
      result = result.filter((a) => a.status === filter.status);
    }

    // Sort by severity (critical first), then by timestamp (newest first)
    result.sort((a, b) => {
      const sevA = SEVERITY_ORDER.indexOf(a.severity);
      const sevB = SEVERITY_ORDER.indexOf(b.severity);
      if (sevA !== sevB) return sevA - sevB;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });

    return result;
  }, [alerts, filter]);

  const acknowledgeAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId
          ? { ...a, status: "acknowledged" as AlertStatus, acknowledged_at: new Date().toISOString() }
          : a,
      ),
    );
    invalidate("executive-alerts", "alert:acknowledged", "alert-center");
  }, [invalidate]);

  const resolveAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId
          ? { ...a, status: "resolved" as AlertStatus, resolved_at: new Date().toISOString() }
          : a,
      ),
    );
    invalidate("executive-alerts", "alert:resolved", "alert-center");
  }, [invalidate]);

  const escalateAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId
          ? { ...a, status: "escalated" as AlertStatus }
          : a,
      ),
    );
    invalidate("executive-alerts", "alert:escalated", "alert-center");
  }, [invalidate]);

  const openCount = useMemo(() => alerts.filter((a) => a.status === "open").length, [alerts]);
  const criticalCount = useMemo(() => alerts.filter((a) => a.severity === "critical" && a.status === "open").length, [alerts]);

  return {
    alerts: filteredAlerts,
    totalAlerts: alerts.length,
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
  };
}

// ── Type Mapping ──────────────────────────────────────────────────

function mapAnomalyType(typeOrCategory: string): AlertType {
  const map: Record<string, AlertType> = {
    // Backend category values
    sla: "sla_breach",
    volume: "workflow_bottleneck",
    risk: "compliance_escalation",
    performance: "provider_instability",
    quality: "ai_drift",
    cost: "workflow_bottleneck",
    workload: "reviewer_overload",
    // Legacy type values
    stuck_workflow: "workflow_bottleneck",
    error_spike: "provider_instability",
    sla_breach: "sla_breach",
    unusual_pattern: "suspicious_activity",
    reviewer_overload: "reviewer_overload",
    ai_drift: "ai_drift",
    ingestion_backlog: "ingestion_backlog",
    compliance: "compliance_escalation",
    replay: "replay_inconsistency",
    vendor_concentration: "vendor_concentration_spike",
  };
  return map[typeOrCategory] ?? "workflow_bottleneck";
}

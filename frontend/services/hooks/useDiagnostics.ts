/**
 * useDiagnostics — React hooks for the observability diagnostics API.
 *
 * Provides:
 *   - useSystemDiagnostics — Aggregate system diagnostics
 *   - useEventChain — Correlation timeline viewer
 *   - useOutboxDiagnostics — Outbox audit explorer
 *   - useWorkerDiagnostics — Worker heartbeat/queue monitoring
 *
 * Usage:
 *   const { data: diagnostics, isLoading } = useSystemDiagnostics();
 *   const { data: chain } = useEventChain("corr-123");
 *   const { data: outbox } = useOutboxDiagnostics();
 *   const { data: workers } = useWorkerDiagnostics();
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api/client";

// ── Types ─────────────────────────────────────────────────────────

export interface DiagnosticsData {
  timestamp: string;
  uptime_seconds: number;
  websocket: {
    active_connections: number;
    tenant_count: number;
    messages_sent: number;
    subscriptions: Record<string, number>;
    uptime_seconds: number;
  };
  reconnect_storms: Record<string, { recent_reconnects: number; storm_detected: boolean }>;
  prometheus: Record<string, number>;
  database: Record<string, unknown>;
}

export interface EventChainItem {
  event_id: string;
  event_type: string;
  event_version: string;
  sequence_id: number;
  delivery_state: string;
  delivery_attempts: number;
  last_error: string | null;
  delivered_at: string | null;
  acknowledged_at: string | null;
  dead_letter_reason: string | null;
  created_at: string | null;
  payload: Record<string, unknown> | null;
}

export interface OutboxDiagnosticsData {
  counts: Record<string, number>;
  pending_count: number;
  recent_events: Array<{
    event_id: string;
    event_type: string;
    delivery_state: string;
    delivery_attempts: number;
    correlation_id: string | null;
    created_at: string | null;
  }>;
  dead_letters: Array<{
    event_id: string;
    event_type: string;
    delivery_attempts: number;
    last_error: string | null;
    dead_letter_reason: string | null;
    dead_letter_at: string | null;
    correlation_id: string | null;
  }>;
}

export interface WorkerDiagnosticsData {
  workers: Record<string, {
    queue: string;
    last_heartbeat: string | null;
    status: string;
    tasks_completed: number;
    tasks_failed: number;
  }>;
  queues: Record<string, number>;
  stuck_jobs: Record<string, number>;
  heartbeats: Array<Record<string, unknown>>;
}

// ── Query Keys ────────────────────────────────────────────────────

export const diagnosticsKeys = {
  all: ["diagnostics"] as const,
  system: () => [...diagnosticsKeys.all, "system"] as const,
  eventChain: (correlationId: string) => [...diagnosticsKeys.all, "events", correlationId] as const,
  outbox: () => [...diagnosticsKeys.all, "outbox"] as const,
  workers: () => [...diagnosticsKeys.all, "workers"] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────

export function useSystemDiagnostics() {
  return useQuery({
    queryKey: diagnosticsKeys.system(),
    queryFn: () => api.get<DiagnosticsData>("/admin/diagnostics"),
    refetchInterval: 15_000, // Poll every 15s
    staleTime: 10_000,
  });
}

export function useEventChain(correlationId: string | null) {
  return useQuery({
    queryKey: diagnosticsKeys.eventChain(correlationId ?? ""),
    queryFn: () =>
      api.get<EventChainItem[]>(
        `/admin/diagnostics/events?correlation_id=${encodeURIComponent(correlationId ?? "")}`,
      ),
    enabled: !!correlationId,
    staleTime: 30_000,
  });
}

export function useOutboxDiagnostics(tenantId?: string) {
  return useQuery({
    queryKey: [...diagnosticsKeys.outbox(), tenantId],
    queryFn: () =>
      api.get<OutboxDiagnosticsData>(
        tenantId
          ? `/admin/diagnostics/outbox?tenant_id=${encodeURIComponent(tenantId)}`
          : "/admin/diagnostics/outbox",
      ),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}

export function useWorkerDiagnostics() {
  return useQuery({
    queryKey: diagnosticsKeys.workers(),
    queryFn: () => api.get<WorkerDiagnosticsData>("/admin/diagnostics/workers"),
    refetchInterval: 15_000,
    staleTime: 10_000,
  });
}

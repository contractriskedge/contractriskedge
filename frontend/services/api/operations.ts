/**
 * Operations & Observability API client.
 *
 * Endpoints:
 *   GET  /api/v1/operations/health          — System Health Dashboard
 *   GET  /api/v1/operations/health/{service} — Single service health
 *   GET  /api/v1/operations/queues           — Queue status
 *   GET  /api/v1/operations/scheduler        — Scheduler status
 *   GET  /api/v1/operations/integrations     — Integration health
 *   GET  /api/v1/operations/errors           — Error dashboard
 *   GET  /api/v1/operations/slow             — Slow operations
 *   GET  /api/v1/operations/alerts           — Active alerts
 *   POST /api/v1/operations/support-bundle   — Download support bundle
 */

import { api } from "@/services/api/client";

// ── Types ──────────────────────────────────────────────────────────

export interface ServiceHealth {
  name: string;
  status: "healthy" | "warning" | "degraded" | "failed" | "unknown";
  last_checked: string | null;
  response_time_ms: number | null;
  error?: string;
  detail?: string;
}

export interface SystemHealth {
  status: "healthy" | "warning" | "critical";
  uptime_seconds: number;
  version: string;
  environment: string;
  healthy_count: number;
  total_count: number;
  tenant_count: number | null;
  services: Record<string, ServiceHealth>;
}

export interface QueueStatus {
  queues: Record<string, number>;
  dead_letter_count: number;
  total_pending: number;
  has_backlog: boolean;
  status: string;
  error?: string;
}

export interface ScheduledTask {
  worker: string;
  task_name: string;
  eta: string;
  priority: number;
}

export interface ActiveTask {
  worker: string;
  task_name: string;
  started: number;
  args: string;
}

export interface SchedulerStatus {
  scheduled_tasks: ScheduledTask[];
  active_tasks: ActiveTask[];
  total_scheduled: number;
  total_active: number;
  status: string;
  error?: string;
}

export interface IntegrationHealth {
  name: string;
  status: string;
  last_checked: string | null;
  response_time_ms: number | null;
  error?: string;
  detail?: string;
}

export interface ErrorDashboard {
  categories: Record<string, number>;
  trends: Record<string, { label: string; count: number }>;
  error?: string;
}

export interface SlowOperation {
  method?: string;
  path?: string;
  duration_ms?: number;
  duration_seconds?: number;
  timestamp?: string;
  status?: string;
  correlation_id?: string;
}

export interface SlowOperations {
  apis: SlowOperation[];
  queries: SlowOperation[];
  workflows: SlowOperation[];
  searches: SlowOperation[];
  error?: string;
}

export interface Alert {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info";
  source: string;
  timestamp: string;
}

// ── API Functions ──────────────────────────────────────────────────

export async function fetchSystemHealth(): Promise<SystemHealth> {
  return api.get("/operations/health");
}

export async function fetchServiceHealth(service: string): Promise<ServiceHealth> {
  return api.get(`/operations/health/${service}`);
}

export async function fetchQueueStatus(): Promise<QueueStatus> {
  return api.get("/operations/queues");
}

export async function fetchSchedulerStatus(): Promise<SchedulerStatus> {
  return api.get("/operations/scheduler");
}

export async function fetchIntegrationHealth(): Promise<IntegrationHealth[]> {
  return api.get("/operations/integrations");
}

export async function fetchErrorDashboard(): Promise<ErrorDashboard> {
  return api.get("/operations/errors");
}

export async function fetchSlowOperations(): Promise<SlowOperations> {
  return api.get("/operations/slow");
}

export async function fetchAlerts(): Promise<Alert[]> {
  return api.get("/operations/alerts");
}

export async function downloadSupportBundle(): Promise<Blob> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const base = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
  const response = await fetch(`${base}/operations/support-bundle`, {
    method: "POST",
    headers,
  });

  if (!response.ok) {
    throw new Error(`Support bundle generation failed: ${response.status}`);
  }

  return response.blob();
}

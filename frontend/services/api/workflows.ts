/**
 * Workflows API service — real API client for workflow operations.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { api } from "@/services/api/client";

export interface WorkflowKpi {
  label: string;
  value: number;
  change: number;
  trend: "up" | "down" | "neutral";
}

export interface WorkflowRecord {
  id: string;
  name: string;
  type: string;
  status: "active" | "paused" | "completed" | "failed";
  priority: "critical" | "high" | "medium" | "low";
  assigned_to: string;
  sla_deadline: string;
  sla_breached: boolean;
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDashboardData {
  kpis: WorkflowKpi[];
  workflows: WorkflowRecord[];
  total_workflows: number;
  active_workflows: number;
  sla_breaches: number;
  avg_completion_time_hours: number;
}

export async function fetchWorkflowDashboard(): Promise<WorkflowDashboardData> {
  return api.get<WorkflowDashboardData>("/workflows/dashboard");
}

export async function fetchWorkflows(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  type?: string;
  priority?: string;
}): Promise<{ data: WorkflowRecord[]; pagination: { page: number; page_size: number; total: number; total_pages: number } }> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.status) searchParams.set("status", params.status);
  if (params?.type) searchParams.set("type", params.type);
  if (params?.priority) searchParams.set("priority", params.priority);

  const qs = searchParams.toString();
  return api.get(`/workflows${qs ? `?${qs}` : ""}`);
}

/**
 * Admin API service — real API client for admin console operations.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { api } from "@/services/api/client";

export interface AdminKpi {
  label: string;
  value: number;
  change: number;
  trend: "up" | "down" | "neutral";
}

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string;
  status: "active" | "inactive" | "suspended";
  last_login: string;
  mfa_enabled: boolean;
  created_at: string;
}

export interface AdminAuditEvent {
  id: string;
  event_type: string;
  actor_id: string;
  actor_name: string;
  resource_type: string;
  resource_id: string;
  action: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

export interface AdminDashboardData {
  kpis: AdminKpi[];
  total_users: number;
  active_users_30d: number;
  total_tenants: number;
  total_uploads: number;
  total_reviews: number;
  audit_events_24h: number;
  system_health: "healthy" | "degraded" | "unhealthy";
}

export async function fetchAdminDashboard(): Promise<AdminDashboardData> {
  return api.get<AdminDashboardData>("/admin/dashboard");
}

export async function fetchAdminUsers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  status?: string;
}): Promise<{ data: AdminUser[]; pagination: { page: number; page_size: number; total: number; total_pages: number } }> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.search) searchParams.set("search", params.search);
  if (params?.role) searchParams.set("role", params.role);
  if (params?.status) searchParams.set("status", params.status);

  const qs = searchParams.toString();
  return api.get(`/admin/users${qs ? `?${qs}` : ""}`);
}

export async function fetchAuditLogs(params?: {
  page?: number;
  page_size?: number;
  event_type?: string;
  actor_id?: string;
  days?: number;
}): Promise<{ data: AdminAuditEvent[]; pagination: { page: number; page_size: number; total: number; total_pages: number } }> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.event_type) searchParams.set("event_type", params.event_type);
  if (params?.actor_id) searchParams.set("actor_id", params.actor_id);
  if (params?.days) searchParams.set("days", String(params.days));

  const qs = searchParams.toString();
  return api.get(`/admin/audit-logs${qs ? `?${qs}` : ""}`);
}

/**
 * Admin query hooks — TanStack Query wrappers for admin API.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  fetchAdminDashboard,
  fetchAdminUsers,
  fetchAuditLogs,
} from "@/services/api/admin";

export const adminKeys = {
  all: ["admin"] as const,
  dashboard: () => [...adminKeys.all, "dashboard"] as const,
  users: (params?: Record<string, unknown>) => [...adminKeys.all, "users", params] as const,
  auditLogs: (params?: Record<string, unknown>) => [...adminKeys.all, "audit-logs", params] as const,
};

export function useAdminDashboard() {
  return useQuery({
    queryKey: adminKeys.dashboard(),
    queryFn: fetchAdminDashboard,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useAdminUsers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  status?: string;
}) {
  return useQuery({
    queryKey: adminKeys.users(params),
    queryFn: () => fetchAdminUsers(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

export function useAuditLogs(params?: {
  page?: number;
  page_size?: number;
  event_type?: string;
  actor_id?: string;
  days?: number;
}) {
  return useQuery({
    queryKey: adminKeys.auditLogs(params),
    queryFn: () => fetchAuditLogs(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

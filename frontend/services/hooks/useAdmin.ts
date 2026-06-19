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

export function useAdminDashboard(enabled = true) {
  return useQuery({
    queryKey: adminKeys.dashboard(),
    queryFn: fetchAdminDashboard,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    enabled,
  });
}

export function useAdminUsers(
  params?: {
    page?: number;
    page_size?: number;
    search?: string;
    role?: string;
    status?: string;
  },
  enabled = true,
) {
  return useQuery({
    queryKey: adminKeys.users(params),
    queryFn: () => fetchAdminUsers(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    enabled,
  });
}

export function useAuditLogs(
  params?: {
    page?: number;
    page_size?: number;
    event_type?: string;
    actor_id?: string;
    status?: string;
    days?: number;
    from_date?: string;
    to_date?: string;
  },
  enabled = true,
) {
  return useQuery({
    queryKey: adminKeys.auditLogs(params),
    queryFn: () => fetchAuditLogs(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    enabled,
  });
}

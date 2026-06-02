/**
 * Workflows query hooks — TanStack Query wrappers for workflows API.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  fetchWorkflowDashboard,
  fetchWorkflows,
} from "@/services/api/workflows";

export const workflowKeys = {
  all: ["workflows"] as const,
  dashboard: () => [...workflowKeys.all, "dashboard"] as const,
  list: (params?: Record<string, unknown>) => [...workflowKeys.all, "list", params] as const,
};

export function useWorkflowDashboard() {
  return useQuery({
    queryKey: workflowKeys.dashboard(),
    queryFn: fetchWorkflowDashboard,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useWorkflows(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  type?: string;
  priority?: string;
}) {
  return useQuery({
    queryKey: workflowKeys.list(params),
    queryFn: () => fetchWorkflows(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

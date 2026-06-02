/**
 * Contracts query hooks — TanStack Query wrappers for contracts API.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  fetchContracts,
  fetchContractKpis,
  fetchContractById,
  fetchSavedViews,
} from "@/services/api/contracts";

export const contractKeys = {
  all: ["contracts"] as const,
  list: (params?: Record<string, unknown>) => [...contractKeys.all, "list", params] as const,
  detail: (id: string) => [...contractKeys.all, "detail", id] as const,
  kpis: () => [...contractKeys.all, "kpis"] as const,
  views: () => [...contractKeys.all, "views"] as const,
};

export function useContracts(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  vendor?: string;
  risk_level?: string;
  status?: string;
}) {
  return useQuery({
    queryKey: contractKeys.list(params),
    queryFn: () => fetchContracts(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

export function useContractKpis() {
  return useQuery({
    queryKey: contractKeys.kpis(),
    queryFn: fetchContractKpis,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useContractById(id: string) {
  return useQuery({
    queryKey: contractKeys.detail(id),
    queryFn: () => fetchContractById(id),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useSavedViews() {
  return useQuery({
    queryKey: contractKeys.views(),
    queryFn: fetchSavedViews,
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
  });
}

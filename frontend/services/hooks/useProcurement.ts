/**
 * Procurement query hooks — TanStack Query wrappers for procurement API.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  fetchProcurementDashboard,
  fetchSuppliers,
  fetchSupplierById,
} from "@/services/api/procurement";

export const procurementKeys = {
  all: ["procurement"] as const,
  dashboard: () => [...procurementKeys.all, "dashboard"] as const,
  suppliers: (params?: Record<string, unknown>) => [...procurementKeys.all, "suppliers", params] as const,
  supplier: (id: string) => [...procurementKeys.all, "supplier", id] as const,
};

export function useProcurementDashboard() {
  return useQuery({
    queryKey: procurementKeys.dashboard(),
    queryFn: fetchProcurementDashboard,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useSuppliers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  category?: string;
  risk_level?: string;
  status?: string;
}) {
  return useQuery({
    queryKey: procurementKeys.suppliers(params),
    queryFn: () => fetchSuppliers(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

export function useSupplierById(id: string) {
  return useQuery({
    queryKey: procurementKeys.supplier(id),
    queryFn: () => fetchSupplierById(id),
    enabled: !!id,
    staleTime: 60_000,
  });
}

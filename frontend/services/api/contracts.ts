/**
 * Contracts API service — real API client for contract operations.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { api } from "@/services/api/client";
import type { ContractRecord, ContractKpi, SavedView, ContractFilterState } from "@/components/dashboard/contracts/types";

export interface ContractsListResponse {
  data: ContractRecord[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface ContractsKpiResponse {
  total_contracts: number;
  active_reviews: number;
  pending_reviews: number;
  high_risk_count: number;
  expiring_soon: number;
  avg_risk_score: number;
  total_value_at_risk: number;
}

export async function fetchContracts(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  vendor?: string;
  risk_level?: string;
  status?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}): Promise<ContractsListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.search) searchParams.set("search", params.search);
  if (params?.vendor) searchParams.set("vendor", params.vendor);
  if (params?.risk_level) searchParams.set("risk_level", params.risk_level);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params?.sort_order) searchParams.set("sort_order", params.sort_order);

  const qs = searchParams.toString();
  return api.get<ContractsListResponse>(`/contracts${qs ? `?${qs}` : ""}`);
}

export async function fetchContractKpis(): Promise<ContractsKpiResponse> {
  return api.get<ContractsKpiResponse>("/contracts/kpis");
}

export async function fetchContractById(id: string): Promise<ContractRecord> {
  return api.get<ContractRecord>(`/contracts/${id}`);
}

export async function fetchSavedViews(): Promise<SavedView[]> {
  return api.get<SavedView[]>("/contracts/views");
}

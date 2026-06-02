/**
 * Procurement API service — real API client for procurement/vendor operations.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { api } from "@/services/api/client";

export interface ProcurementKpi {
  label: string;
  value: number;
  change: number;
  trend: "up" | "down" | "neutral";
  format?: "currency" | "percentage" | "number";
}

export interface SupplierRecord {
  id: string;
  name: string;
  category: string;
  risk_score: number;
  contract_value: number;
  status: "active" | "under_review" | "onboarding" | "expired";
  renewal_date: string;
  sla_compliance: number;
  incidents_30d: number;
  critical_findings: number;
  last_reviewed: string;
}

export interface ProcurementDashboardData {
  kpis: ProcurementKpi[];
  suppliers: SupplierRecord[];
  total_suppliers: number;
  high_risk_suppliers: number;
  avg_risk_score: number;
  total_contract_value: number;
}

export async function fetchProcurementDashboard(): Promise<ProcurementDashboardData> {
  return api.get<ProcurementDashboardData>("/procurement/dashboard");
}

export async function fetchSuppliers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  category?: string;
  risk_level?: string;
  status?: string;
}): Promise<{ data: SupplierRecord[]; pagination: { page: number; page_size: number; total: number; total_pages: number } }> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.search) searchParams.set("search", params.search);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.risk_level) searchParams.set("risk_level", params.risk_level);
  if (params?.status) searchParams.set("status", params.status);

  const qs = searchParams.toString();
  return api.get(`/procurement/suppliers${qs ? `?${qs}` : ""}`);
}

export async function fetchSupplierById(id: string): Promise<SupplierRecord> {
  return api.get<SupplierRecord>(`/procurement/suppliers/${id}`);
}

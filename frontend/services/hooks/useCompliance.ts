/**
 * Compliance query hooks — TanStack Query wrappers for compliance API.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchComplianceDashboard,
  fetchComplianceFrameworks,
  fetchComplianceControls,
  fetchComplianceAssessments,
  fetchComplianceFindings,
  fetchComplianceExceptions,
  fetchComplianceEvidence,
  fetchComplianceScan,
} from "@/services/api/compliance";

export const complianceKeys = {
  all: ["compliance"] as const,
  dashboard: () => [...complianceKeys.all, "dashboard"] as const,
  frameworks: (params?: Record<string, unknown>) => [...complianceKeys.all, "frameworks", params] as const,
  controls: (params?: Record<string, unknown>) => [...complianceKeys.all, "controls", params] as const,
  assessments: (params?: Record<string, unknown>) => [...complianceKeys.all, "assessments", params] as const,
  findings: (params?: Record<string, unknown>) => [...complianceKeys.all, "findings", params] as const,
  exceptions: (params?: Record<string, unknown>) => [...complianceKeys.all, "exceptions", params] as const,
  evidence: (params?: Record<string, unknown>) => [...complianceKeys.all, "evidence", params] as const,
};

export function useComplianceDashboard() {
  return useQuery({
    queryKey: complianceKeys.dashboard(),
    queryFn: fetchComplianceDashboard,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useComplianceFrameworks(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: complianceKeys.frameworks(params),
    queryFn: () => fetchComplianceFrameworks(params),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useComplianceControls(params?: { framework_id?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: complianceKeys.controls(params),
    queryFn: () => fetchComplianceControls(params),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useComplianceAssessments(params?: { framework_id?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: complianceKeys.assessments(params),
    queryFn: () => fetchComplianceAssessments(params),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useComplianceFindings(params?: {
  assessment_id?: string;
  status?: string;
  severity?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: complianceKeys.findings(params),
    queryFn: () => fetchComplianceFindings(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

export function useComplianceExceptions(params?: { status?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: complianceKeys.exceptions(params),
    queryFn: () => fetchComplianceExceptions(params),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useComplianceEvidence(params?: { framework?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: complianceKeys.evidence(params),
    queryFn: () => fetchComplianceEvidence(params),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useComplianceScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fetchComplianceScan,
    onSuccess: () => {
      // Invalidate all compliance queries to refresh dashboard + lists
      queryClient.invalidateQueries({ queryKey: complianceKeys.all });
    },
  });
}

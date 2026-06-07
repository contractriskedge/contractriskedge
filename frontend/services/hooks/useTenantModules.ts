/**
 * Tenant Settings React Query hooks — Policy Packs, Scoring Overrides,
 * Compliance Packs, and Tenant Summary.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tenantService, tenantKeys } from "@/services/api/tenant";
import type {
  PolicyPackCreate,
  PolicyPackResponse,
  ScoringOverrideCreate,
  ScoringOverrideResponse,
  CompliancePackCreate,
  CompliancePackResponse,
} from "@/services/api/tenant";

// ── Policy Packs ──────────────────────────────────────────────────

export function usePolicyPacks() {
  return useQuery({
    queryKey: tenantKeys.policyPacks(),
    queryFn: tenantService.getPolicyPacks,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useCreatePolicyPack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pack: PolicyPackCreate) => tenantService.createPolicyPack(pack),
    onSuccess: () => qc.invalidateQueries({ queryKey: tenantKeys.policyPacks() }),
  });
}

export function useDeletePolicyPack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (packId: string) => tenantService.deletePolicyPack(packId),
    onSuccess: () => qc.invalidateQueries({ queryKey: tenantKeys.policyPacks() }),
  });
}

// ── Scoring Overrides ─────────────────────────────────────────────

export function useScoringOverrides() {
  return useQuery({
    queryKey: tenantKeys.scoringOverrides(),
    queryFn: tenantService.getScoringOverrides,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useCreateScoringOverride() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (override: ScoringOverrideCreate) =>
      tenantService.createScoringOverride(override),
    onSuccess: () => qc.invalidateQueries({ queryKey: tenantKeys.scoringOverrides() }),
  });
}

export function useDeleteScoringOverride() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (overrideId: string) =>
      tenantService.deleteScoringOverride(overrideId),
    onSuccess: () => qc.invalidateQueries({ queryKey: tenantKeys.scoringOverrides() }),
  });
}

// ── Compliance Packs ──────────────────────────────────────────────

export function useCompliancePacks() {
  return useQuery({
    queryKey: tenantKeys.compliancePacks(),
    queryFn: tenantService.getCompliancePacks,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useCreateCompliancePack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pack: CompliancePackCreate) =>
      tenantService.createCompliancePack(pack),
    onSuccess: () => qc.invalidateQueries({ queryKey: tenantKeys.compliancePacks() }),
  });
}

// ── Tenant Summary ────────────────────────────────────────────────

export function useTenantSummary() {
  return useQuery({
    queryKey: tenantKeys.summary(),
    queryFn: tenantService.getConfigSummary,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as workflowAdmin from "@/services/api/workflowAdmin";

// ── Query Key Factory ──────────────────────────────────────────────

export const workflowAdminKeys = {
  all: ["workflow-admin"] as const,
  packs: (params?: Record<string, unknown>) =>
    [...workflowAdminKeys.all, "packs", params] as const,
  pack: (id: string) => [...workflowAdminKeys.all, "pack", id] as const,
  versions: (packId: string) => [...workflowAdminKeys.all, "versions", packId] as const,
  validation: (packId: string, versionId: string) =>
    [...workflowAdminKeys.all, "validate", packId, versionId] as const,
  impact: (packId: string, versionId: string) =>
    [...workflowAdminKeys.all, "impact", packId, versionId] as const,
  simulation: (packId: string, versionId: string) =>
    [...workflowAdminKeys.all, "simulate", packId, versionId] as const,
  analytics: (days?: number) =>
    [...workflowAdminKeys.all, "analytics", days] as const,
  packAnalytics: (packId: string) =>
    [...workflowAdminKeys.all, "pack-analytics", packId] as const,
};

// ── Packs ──────────────────────────────────────────────────────────

export function useWorkflowPacks(params?: {
  category?: string;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: workflowAdminKeys.packs(params as Record<string, unknown>),
    queryFn: () => workflowAdmin.fetchWorkflowPacks(params),
    staleTime: 30_000,
  });
}

export function useWorkflowPack(packId: string) {
  return useQuery({
    queryKey: workflowAdminKeys.pack(packId),
    queryFn: () => workflowAdmin.fetchWorkflowPack(packId),
    enabled: !!packId,
    staleTime: 30_000,
  });
}

export function useCreateWorkflowPack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: workflowAdmin.createWorkflowPack,
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowAdminKeys.packs() }),
  });
}

export function useUpdateWorkflowPack(packId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<workflowAdmin.WorkflowPackDetail>) =>
      workflowAdmin.updateWorkflowPack(packId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workflowAdminKeys.pack(packId) });
      qc.invalidateQueries({ queryKey: workflowAdminKeys.packs() });
    },
  });
}

export function useDeleteWorkflowPack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: workflowAdmin.deleteWorkflowPack,
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowAdminKeys.packs() }),
  });
}

export function useCloneWorkflowPack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ packId, name }: { packId: string; name?: string }) =>
      workflowAdmin.cloneWorkflowPack(packId, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowAdminKeys.packs() }),
  });
}

export function useToggleFavorite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: workflowAdmin.toggleFavorite,
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowAdminKeys.packs() }),
  });
}

// ── Versions ───────────────────────────────────────────────────────

export function useVersions(packId: string) {
  return useQuery({
    queryKey: workflowAdminKeys.versions(packId),
    queryFn: () => workflowAdmin.fetchVersions(packId),
    enabled: !!packId,
  });
}

export function useCreateVersion(packId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { stages: workflowAdmin.StageDefinition[]; rules: workflowAdmin.RuleDefinition[]; change_summary?: string }) =>
      workflowAdmin.createVersion(packId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workflowAdminKeys.versions(packId) });
      qc.invalidateQueries({ queryKey: workflowAdminKeys.pack(packId) });
    },
  });
}

export function usePublishVersion(packId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, data }: { versionId: string; data?: { effective_date?: string; change_summary?: string } }) =>
      workflowAdmin.publishVersion(packId, versionId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workflowAdminKeys.versions(packId) });
      qc.invalidateQueries({ queryKey: workflowAdminKeys.pack(packId) });
      qc.invalidateQueries({ queryKey: workflowAdminKeys.packs() });
    },
  });
}

// ── Validation & Impact ────────────────────────────────────────────

export function useValidation(packId: string, versionId: string) {
  return useQuery({
    queryKey: workflowAdminKeys.validation(packId, versionId),
    queryFn: () => workflowAdmin.validateWorkflowPack(packId, versionId),
    enabled: !!packId && !!versionId,
  });
}

export function useImpact(packId: string, versionId: string) {
  return useQuery({
    queryKey: workflowAdminKeys.impact(packId, versionId),
    queryFn: () => workflowAdmin.analyzeImpact(packId, versionId),
    enabled: !!packId && !!versionId,
  });
}

// ── Simulation ─────────────────────────────────────────────────────

export function useSimulation() {
  return useMutation({
    mutationFn: ({ packId, versionId, input }: {
      packId: string;
      versionId: string;
      input: workflowAdmin.SimulationInput;
    }) => workflowAdmin.simulateWorkflow(packId, versionId, input),
  });
}

// ── Analytics ──────────────────────────────────────────────────────

export function useWorkflowAnalytics(days?: number) {
  return useQuery({
    queryKey: workflowAdminKeys.analytics(days),
    queryFn: () => workflowAdmin.fetchWorkflowAnalytics({ days }),
    staleTime: 60_000,
  });
}

export function usePackAnalytics(packId: string) {
  return useQuery({
    queryKey: workflowAdminKeys.packAnalytics(packId),
    queryFn: () => workflowAdmin.fetchPackAnalytics(packId),
    enabled: !!packId,
    staleTime: 60_000,
  });
}

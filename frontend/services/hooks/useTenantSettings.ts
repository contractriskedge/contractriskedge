/**
 * Tenant Settings & Feature Flag React Query hooks.
 *
 * Provides:
 *   useTenantSettings()     — GET/PUT /admin/settings
 *   useFeatureFlags()       — GET /tenant-config/features/definitions + evaluate
 *   useSetFeatureOverride() — POST /tenant-config/features/overrides (mutation)
 *   useDeleteFeatureOverride() — DELETE /tenant-config/features/overrides/{fk}/{tt}/{ti}
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tenantService, tenantKeys } from "@/services/api/tenant";
import type {
  TenantSettingsResponse,
  TenantSettingsUpdate,
  FeatureFlagDefinition,
  FeatureFlagEvaluation,
  FeatureOverrideCreate,
} from "@/services/api/tenant";

// ── useTenantSettings ─────────────────────────────────────────────

export function useTenantSettings() {
  return useQuery({
    queryKey: tenantKeys.config("default"),
    queryFn: tenantService.getSettings,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useUpdateTenantSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (settings: TenantSettingsUpdate) =>
      tenantService.updateSettings(settings),
    onMutate: async (newSettings) => {
      // Cancel in-flight queries
      await queryClient.cancelQueries({ queryKey: tenantKeys.config("default") });
      // Snapshot previous value
      const previous = queryClient.getQueryData<TenantSettingsResponse>(
        tenantKeys.config("default"),
      );
      // Optimistic update
      if (previous) {
        queryClient.setQueryData<TenantSettingsResponse>(
          tenantKeys.config("default"),
          { ...previous, ...newSettings },
        );
      }
      return { previous };
    },
    onError: (_err, _newSettings, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(tenantKeys.config("default"), context.previous);
      }
    },
    onSettled: () => {
      // Always refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: tenantKeys.config("default") });
    },
  });
}

// ── useFeatureFlags ───────────────────────────────────────────────

export function useFeatureFlagDefinitions() {
  return useQuery({
    queryKey: tenantKeys.featureDefinitions(),
    queryFn: tenantService.getFeatureDefinitions,
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function useFeatureFlagEvaluations() {
  return useQuery({
    queryKey: tenantKeys.features("default"),
    queryFn: tenantService.evaluateFeatures,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

export function useSetFeatureOverride() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (override: FeatureOverrideCreate) =>
      tenantService.setFeatureOverride(override),
    onSuccess: () => {
      // Invalidate evaluations so they refetch with the new override
      queryClient.invalidateQueries({ queryKey: tenantKeys.features("default") });
      // Also invalidate settings since features_enabled may have changed
      queryClient.invalidateQueries({ queryKey: tenantKeys.config("default") });
    },
  });
}

export function useDeleteFeatureOverride() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ flagKey, targetType, targetId }: { flagKey: string; targetType: string; targetId: string }) =>
      tenantService.deleteFeatureOverride(flagKey, targetType, targetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantKeys.features("default") });
      queryClient.invalidateQueries({ queryKey: tenantKeys.config("default") });
    },
  });
}

// ── Derived data helper ───────────────────────────────────────────

export interface FeatureFlagWithValue {
  definition: FeatureFlagDefinition;
  evaluation: FeatureFlagEvaluation | undefined;
}

export function useFeatureFlagsWithValues(): {
  data: FeatureFlagWithValue[] | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const { data: definitions, isLoading: defsLoading, error: defsError, refetch: refetchDefs } = useFeatureFlagDefinitions();
  const { data: evaluations, isLoading: evalsLoading, error: evalsError, refetch: refetchEvals } = useFeatureFlagEvaluations();

  const isLoading = defsLoading || evalsLoading;
  const error = defsError || evalsError;

  if (!definitions) {
    return { data: undefined, isLoading, error, refetch: () => { refetchDefs(); refetchEvals(); } };
  }

  const evalMap = new Map<string, FeatureFlagEvaluation>();
  if (evaluations) {
    for (const ev of evaluations) {
      evalMap.set(ev.flag_key, ev);
    }
  }

  const data: FeatureFlagWithValue[] = definitions.map((def) => ({
    definition: def,
    evaluation: evalMap.get(def.flag_key),
  }));

  return {
    data,
    isLoading,
    error,
    refetch: () => { refetchDefs(); refetchEvals(); },
  };
}

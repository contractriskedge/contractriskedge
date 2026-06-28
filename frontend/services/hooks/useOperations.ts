"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import * as operations from "@/services/api/operations";

// ── Query Key Factory ──────────────────────────────────────────────

export const operationsKeys = {
  all: ["operations"] as const,
  health: () => [...operationsKeys.all, "health"] as const,
  serviceHealth: (service: string) => [...operationsKeys.all, "health", service] as const,
  queues: () => [...operationsKeys.all, "queues"] as const,
  scheduler: () => [...operationsKeys.all, "scheduler"] as const,
  integrations: () => [...operationsKeys.all, "integrations"] as const,
  errors: () => [...operationsKeys.all, "errors"] as const,
  slow: () => [...operationsKeys.all, "slow"] as const,
  alerts: () => [...operationsKeys.all, "alerts"] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────

export function useSystemHealth(refreshInterval = 30_000) {
  return useQuery({
    queryKey: operationsKeys.health(),
    queryFn: operations.fetchSystemHealth,
    refetchInterval: refreshInterval,
    staleTime: 15_000,
  });
}

export function useServiceHealth(service: string) {
  return useQuery({
    queryKey: operationsKeys.serviceHealth(service),
    queryFn: () => operations.fetchServiceHealth(service),
    enabled: !!service,
    staleTime: 15_000,
  });
}

export function useQueueStatus(refreshInterval = 15_000) {
  return useQuery({
    queryKey: operationsKeys.queues(),
    queryFn: operations.fetchQueueStatus,
    refetchInterval: refreshInterval,
    staleTime: 10_000,
  });
}

export function useSchedulerStatus(refreshInterval = 30_000) {
  return useQuery({
    queryKey: operationsKeys.scheduler(),
    queryFn: operations.fetchSchedulerStatus,
    refetchInterval: refreshInterval,
    staleTime: 15_000,
  });
}

export function useIntegrationHealth(refreshInterval = 60_000) {
  return useQuery({
    queryKey: operationsKeys.integrations(),
    queryFn: operations.fetchIntegrationHealth,
    refetchInterval: refreshInterval,
    staleTime: 30_000,
  });
}

export function useErrorDashboard(refreshInterval = 60_000) {
  return useQuery({
    queryKey: operationsKeys.errors(),
    queryFn: operations.fetchErrorDashboard,
    refetchInterval: refreshInterval,
    staleTime: 30_000,
  });
}

export function useSlowOperations(refreshInterval = 60_000) {
  return useQuery({
    queryKey: operationsKeys.slow(),
    queryFn: operations.fetchSlowOperations,
    refetchInterval: refreshInterval,
    staleTime: 30_000,
  });
}

export function useAlerts(refreshInterval = 30_000) {
  return useQuery({
    queryKey: operationsKeys.alerts(),
    queryFn: operations.fetchAlerts,
    refetchInterval: refreshInterval,
    staleTime: 15_000,
  });
}

export function useSupportBundle() {
  return useMutation({
    mutationFn: operations.downloadSupportBundle,
  });
}

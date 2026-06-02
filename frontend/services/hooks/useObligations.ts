/**
 * Obligation Management query hooks — TanStack Query wrappers for obligations API.
 * Provides typed hooks for all obligation, SLA, financial, and risk endpoints.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  obligationsService,
  obligationKeys,
} from "@/services/api/obligations";
import type {
  ObligationListParams,
  ObligationCreateRequest,
  ObligationUpdateRequest,
  AiReviewRequest,
  ObligationReminderCreateRequest,
  ObligationEscalationCreateRequest,
} from "@/services/api/obligations";

// ── List / Paginated ──────────────────────────────────────────────

export function useObligations(params?: ObligationListParams) {
  return useQuery({
    queryKey: obligationKeys.list(params),
    queryFn: () => obligationsService.listObligations(params),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

// ── Single Obligation ─────────────────────────────────────────────

export function useObligation(id: string) {
  return useQuery({
    queryKey: obligationKeys.detail(id),
    queryFn: () => obligationsService.getObligation(id),
    enabled: !!id,
    staleTime: 60_000,
  });
}

// ── KPIs / Analytics ──────────────────────────────────────────────

export function useObligationKpis() {
  return useQuery({
    queryKey: obligationKeys.kpis(),
    queryFn: () => obligationsService.getKpis(),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

// ── SLA Performance / Breaches / Vendor Risk / Predictions ────────

export function useSlaPerformance() {
  return useQuery({
    queryKey: obligationKeys.slaPerformance(),
    queryFn: () => obligationsService.getSlaPerformance(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function useSlaBreaches() {
  return useQuery({
    queryKey: obligationKeys.slaBreaches(),
    queryFn: () => obligationsService.getSlaBreaches(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function useVendorRisk() {
  return useQuery({
    queryKey: obligationKeys.vendorRisk(),
    queryFn: () => obligationsService.getVendorRisk(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function useSlaPredictions() {
  return useQuery({
    queryKey: obligationKeys.slaPredictions(),
    queryFn: () => obligationsService.getSlaPredictions(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

// ── Calendar / Upcoming / Overdue ─────────────────────────────────

export function useCalendar(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: [...obligationKeys.calendar(), startDate, endDate],
    queryFn: () => obligationsService.getCalendar(startDate!, endDate!),
    enabled: !!startDate,
    staleTime: 60_000,
  });
}

export function useUpcoming(days?: number) {
  return useQuery({
    queryKey: [...obligationKeys.upcoming(), days],
    queryFn: () => obligationsService.getUpcoming(days ?? 30),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useOverdue() {
  return useQuery({
    queryKey: obligationKeys.overdue(),
    queryFn: () => obligationsService.getOverdue(),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
}

// ── Financial Exposure / Penalties / Value at Risk ────────────────

export function useFinancialExposure() {
  return useQuery({
    queryKey: obligationKeys.financialExposure(),
    queryFn: () => obligationsService.getFinancialExposure(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function usePenalties() {
  return useQuery({
    queryKey: obligationKeys.penalties(),
    queryFn: () => obligationsService.getPenalties(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

export function useValueAtRisk() {
  return useQuery({
    queryKey: obligationKeys.valueAtRisk(),
    queryFn: () => obligationsService.getValueAtRisk(),
    staleTime: 120_000,
    gcTime: 10 * 60_000,
  });
}

// ── Risk Analysis / Escalations / Anomalies / Notification History ─

export function useRiskAnalysis(id: string) {
  return useQuery({
    queryKey: obligationKeys.riskAnalysis(id),
    queryFn: () => obligationsService.getRiskAnalysis(id),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useEscalations() {
  return useQuery({
    queryKey: obligationKeys.escalations(),
    queryFn: () => obligationsService.getEscalations(),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useAnomalies() {
  return useQuery({
    queryKey: obligationKeys.anomalies(),
    queryFn: () => obligationsService.getAnomalies(),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

export function useNotificationHistory() {
  return useQuery({
    queryKey: obligationKeys.notificationHistory(),
    queryFn: () => obligationsService.getNotificationHistory(),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

// ── Mutations (Create / Update / Delete) ──────────────────────────

export function useCreateObligation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ObligationCreateRequest) =>
      obligationsService.createObligation(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationKeys.lists() });
    },
  });
}

export function useUpdateObligation(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ObligationUpdateRequest) =>
      obligationsService.updateObligation(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationKeys.detail(id) });
      qc.invalidateQueries({ queryKey: obligationKeys.lists() });
    },
  });
}

export function useDeleteObligation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      obligationsService.deleteObligation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationKeys.lists() });
    },
  });
}

// ── AI Review ─────────────────────────────────────────────────────

export function useAiReview() {
  return useMutation({
    mutationFn: (body: AiReviewRequest) =>
      obligationsService.aiReview(body),
  });
}

// ── Reminders / Escalations ───────────────────────────────────────

export function useCreateReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ObligationReminderCreateRequest) =>
      obligationsService.createReminder(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationKeys.notificationHistory() });
    },
  });
}

export function useCreateEscalation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ObligationEscalationCreateRequest) =>
      obligationsService.createEscalation(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obligationKeys.escalations() });
      qc.invalidateQueries({ queryKey: obligationKeys.lists() });
    },
  });
}

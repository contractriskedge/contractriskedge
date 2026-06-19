/**
 * React Query hooks for Redline Template API.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { redlineTemplateApi } from "@/services/api/redlineTemplates";
import type { TemplateCreateRequest } from "@/services/api/redlineTemplates";

const COVERAGE_KEY = ["redline-templates", "coverage"];
const MISSING_KEY = ["redline-templates", "missing"];
const LIST_KEY = ["redline-templates", "list"];

export function useCoverage() {
  return useQuery({
    queryKey: COVERAGE_KEY,
    queryFn: () => redlineTemplateApi.getCoverage(),
    refetchInterval: 30_000,
  });
}

export function useMissingTemplates(limit = 20) {
  return useQuery({
    queryKey: [...MISSING_KEY, limit],
    queryFn: () => redlineTemplateApi.getMissing(limit),
  });
}

export function useTemplates(params?: {
  clause_type?: string;
  category?: string;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: [...LIST_KEY, params],
    queryFn: () => redlineTemplateApi.list(params),
  });
}

export function useTemplate(id: string) {
  return useQuery({
    queryKey: [...LIST_KEY, id],
    queryFn: () => redlineTemplateApi.get(id),
    enabled: !!id,
  });
}

export function useCreateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TemplateCreateRequest) => redlineTemplateApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: COVERAGE_KEY });
    },
  });
}

export function useUpdateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<TemplateCreateRequest> }) =>
      redlineTemplateApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: COVERAGE_KEY });
    },
  });
}

export function useDeleteTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => redlineTemplateApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: COVERAGE_KEY });
    },
  });
}

export function useGenerateDraft() {
  return useMutation({
    mutationFn: (data: {
      clause_type: string;
      finding_title: string;
      finding_description: string;
      jurisdiction?: string;
      industry?: string;
      risk_level?: string;
    }) => redlineTemplateApi.generateDraft(data),
  });
}

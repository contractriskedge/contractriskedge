/**
 * TemplateDetailPage — View template detail, versions, usage history.
 */

"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, FileText, Star, Clock, Copy, Archive, Trash2, ExternalLink,
  Loader2, AlertTriangle, History, User, Tag, Layers, CheckCircle2,
  Shield, Search, Eye, XCircle,
} from "lucide-react";
import { api } from "@/services";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";
import type { TemplateDetail, TemplateValidationResult, TemplateDependencyInfo } from "./types";

interface TemplateDetailPageProps {
  templateId: string;
}

export default function TemplateDetailPage({ templateId }: TemplateDetailPageProps) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: template, isLoading, error, refetch } = useQuery<TemplateDetail>({
    queryKey: ["template", templateId],
    queryFn: () => api.get(`/templates/${templateId}`),
    enabled: !!templateId,
    staleTime: 30_000,
  });

  const { data: history } = useQuery({
    queryKey: ["template-history", templateId],
    queryFn: () => api.get(`/templates/${templateId}/history`),
    enabled: !!templateId,
    staleTime: 60_000,
  });

  const { data: validation } = useQuery<TemplateValidationResult>({
    queryKey: ["template-validation", templateId],
    queryFn: () => api.get(`/templates/${templateId}/validate`),
    enabled: !!templateId,
    staleTime: 30_000,
  });

  const { data: dependencies } = useQuery<TemplateDependencyInfo>({
    queryKey: ["template-dependencies", templateId],
    queryFn: () => api.get(`/templates/${templateId}/dependencies`),
    enabled: !!templateId,
    staleTime: 30_000,
  });

  const [showPreview, setShowPreview] = useState(false);
  const [previewContent, setPreviewContent] = useState("");

  const toggleFavMut = useMutation({
    mutationFn: () => api.post(`/templates/${templateId}/favorite`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["template", templateId] }),
  });

  const archiveMut = useMutation({
    mutationFn: () => api.post(`/templates/${templateId}/archive`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["template", templateId] }),
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <CardSkeleton count={1} columns={1} />
      </div>
    );
  }

  if (error || !template) {
    return (
      <div className="p-6 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-sm font-medium text-gray-900 dark:text-white">Template not found</p>
        <button onClick={() => router.push("/templates")} className="mt-3 text-xs text-blue-600 hover:underline">
          Back to Template Library
        </button>
      </div>
    );
  }

  const statusColor: Record<string, string> = {
    draft: "bg-gray-100 text-gray-600",
    under_review: "bg-blue-100 text-blue-600",
    approved: "bg-green-100 text-green-700",
    deprecated: "bg-yellow-100 text-yellow-700",
    archived: "bg-red-100 text-red-600",
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/templates")} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-navy-900 dark:text-white">{template.name}</h1>
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${statusColor[template.status] || "bg-gray-100 text-gray-600"}`}>
                {template.status.replace(/_/g, " ")}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              {template.category?.name ?? "Uncategorized"} · v{template.current_version?.version_number ?? "—"} · {template.usage_count} uses
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => toggleFavMut.mutate()}
            className={`p-2 rounded-lg border ${template.is_favorite ? "border-yellow-300 text-yellow-500 bg-yellow-50" : "border-gray-200 text-gray-400"} hover:bg-gray-50 dark:hover:bg-navy-700`}>
            <Star className="w-4 h-4" fill={template.is_favorite ? "currentColor" : "none"} />
          </button>
          <button onClick={() => router.push(`/templates/${templateId}/generate`)}
            disabled={template.status !== "approved"}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50 disabled:cursor-not-allowed">
            <ExternalLink className="w-4 h-4" /> Use Template
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="col-span-2 space-y-4">
          {/* Description */}
          {template.description && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Description</h3>
              <p className="text-sm text-gray-700 dark:text-gray-300">{template.description}</p>
            </div>
          )}

          {/* Tags */}
          {template.tags.length > 0 && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Tags</h3>
              <div className="flex flex-wrap gap-1.5">
                {template.tags.map((tag) => (
                  <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-700 dark:text-navy-200">{tag}</span>
                ))}
              </div>
            </div>
          )}

          {/* Template Preview */}
          {template.current_version?.placeholder_content && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Template Preview</h3>
              <pre className="text-[10px] text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono bg-gray-50 dark:bg-navy-900 p-3 rounded max-h-96 overflow-y-auto">
                {template.current_version.placeholder_content}
              </pre>
            </div>
          )}

          {/* Variables */}
          {template.current_version?.variables && template.current_version.variables.length > 0 && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Variables ({template.current_version.variables.length})</h3>
              <div className="grid grid-cols-2 gap-2">
                {template.current_version.variables.map((v) => (
                  <div key={v.key} className="flex items-center gap-2 p-2 rounded bg-gray-50 dark:bg-navy-900">
                    <span className="text-[10px] font-mono font-medium text-navy-700 dark:text-navy-200">{`{{${v.key}}}`}</span>
                    <span className="text-[9px] text-gray-500">{v.label}</span>
                    <span className="text-[8px] px-1 py-0.5 rounded bg-gray-200 dark:bg-navy-700 text-gray-500 ml-auto">{v.field_type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Version History */}
          {template.versions.length > 0 && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Version History ({template.versions.length})</h3>
              <div className="space-y-2">
                {template.versions.map((v) => (
                  <div key={v.id} className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-navy-900">
                    <div className="flex items-center gap-2">
                      <Layers className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-[11px] font-medium text-navy-900 dark:text-white">v{v.version_number}</span>
                      {v.label && <span className="text-[10px] text-gray-500">{v.label}</span>}
                      {v.id === template.current_version?.id && (
                        <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">Current</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[9px] text-gray-400">
                      <User className="w-3 h-3" /> {v.created_by}
                      <Clock className="w-3 h-3" /> {v.created_at ? new Date(v.created_at).toLocaleDateString() : "—"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Info */}
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Details</h3>
            <div className="space-y-2 text-[11px]">
              <div className="flex justify-between">
                <span className="text-gray-500">Owner</span>
                <span className="font-medium text-navy-900 dark:text-white">{template.owner || "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Department</span>
                <span className="font-medium text-navy-900 dark:text-white">{template.department || "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Created By</span>
                <span className="font-medium text-navy-900 dark:text-white">{template.created_by}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Created</span>
                <span className="font-medium text-navy-900 dark:text-white">{template.created_at ? new Date(template.created_at).toLocaleDateString() : "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Updated</span>
                <span className="font-medium text-navy-900 dark:text-white">{template.updated_at ? new Date(template.updated_at).toLocaleDateString() : "—"}</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Actions</h3>
            <div className="space-y-2">
              <button onClick={() => router.push(`/templates/${templateId}/edit`)}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-navy-600 dark:text-gray-300 dark:hover:bg-navy-700">
                <FileText className="w-3.5 h-3.5" /> Edit Template
              </button>
              <button
                onClick={async () => {
                  try {
                    const resp = await api.post<{ preview_content?: string }>(`/templates/${templateId}/preview`, {
                      template_id: templateId,
                      variable_values: {},
                      title: `${template.name} - Preview`,
                    });
                    setPreviewContent(resp.preview_content || "No preview available");
                    setShowPreview(true);
                  } catch { /* ignore */ }
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-navy-600 dark:text-gray-300 dark:hover:bg-navy-700">
                <Eye className="w-3.5 h-3.5" /> Preview
              </button>
              <button onClick={() => { if (confirm("Archive this template?")) archiveMut.mutate(); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-navy-600 dark:text-gray-300 dark:hover:bg-navy-700">
                <Archive className="w-3.5 h-3.5" /> Archive
              </button>
            </div>
          </div>

          {/* Validation Results */}
          {validation && (
            <div className={`rounded-lg border p-4 ${
              validation.is_valid
                ? "border-green-200 bg-green-50 dark:border-green-700 dark:bg-green-900/20"
                : "border-yellow-200 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-900/20"
            }`}>
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
                <Shield className="w-3 h-3 inline mr-1" />
                Validation
              </h3>
              <div className="flex items-center gap-2 mb-2">
                {validation.is_valid ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-yellow-500" />
                )}
                <span className={`text-xs font-medium ${
                  validation.is_valid ? "text-green-700" : "text-yellow-700"
                }`}>
                  {validation.is_valid ? "Ready to publish" : `${validation.issues.length} issue(s)`}
                </span>
              </div>
              <div className="space-y-1 text-[9px] text-gray-600">
                <p>{validation.placeholder_count} placeholders · {validation.mapped_count} mapped</p>
                {validation.duplicate_count > 0 && (
                  <p className="text-yellow-600">{validation.duplicate_count} duplicate(s)</p>
                )}
                {validation.unused_variables.length > 0 && (
                  <p className="text-yellow-600">Unused: {validation.unused_variables.join(", ")}</p>
                )}
                {validation.missing_placeholders.length > 0 && (
                  <p className="text-red-600">Missing: {validation.missing_placeholders.join(", ")}</p>
                )}
              </div>
              {validation.issues.length > 0 && (
                <div className="mt-2 space-y-1">
                  {validation.issues.map((issue, i) => (
                    <div key={i} className={`text-[9px] px-2 py-1 rounded ${
                      issue.severity === "error" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                    }`}>
                      {issue.message}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Dependency Info */}
          {dependencies && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
                <Search className="w-3 h-3 inline mr-1" />
                Dependencies
              </h3>
              <div className="space-y-2 text-[10px]">
                <div className="flex justify-between">
                  <span className="text-gray-500">Generated Contracts</span>
                  <span className="font-medium text-navy-900 dark:text-white">{dependencies.generated_contract_count}</span>
                </div>
                {dependencies.last_used && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Last Used</span>
                    <span className="font-medium text-navy-900 dark:text-white">
                      {new Date(dependencies.last_used).toLocaleDateString()}
                    </span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-500">Can Archive</span>
                  <span className={dependencies.can_archive ? "text-green-600" : "text-red-600"}>
                    {dependencies.can_archive ? "Yes" : "No"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Can Delete</span>
                  <span className={dependencies.can_delete ? "text-green-600" : "text-red-600"}>
                    {dependencies.can_delete ? "Yes" : "No"}
                  </span>
                </div>
                {dependencies.blocking_reasons.length > 0 && (
                  <div className="mt-2 p-2 rounded bg-yellow-50 text-yellow-700 text-[9px]">
                    {dependencies.blocking_reasons.map((r, i) => (
                      <div key={i} className="flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> {r}</div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Usage History */}
          {Array.isArray(history) && history.length > 0 && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Recent Activity</h3>
              <div className="space-y-2">
                {history.slice(0, 5).map((entry: any) => (
                  <div key={entry.id} className="flex items-start gap-2 text-[10px]">
                    <History className="w-3 h-3 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-gray-700 dark:text-gray-300 capitalize">{entry.action.replace(/_/g, " ")}</p>
                      <p className="text-gray-400">{entry.actor_id} · {entry.created_at ? new Date(entry.created_at).toLocaleDateString() : "—"}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShowPreview(false)}>
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl max-w-3xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-navy-900 dark:text-white">Template Preview</h2>
                <button onClick={() => setShowPreview(false)} className="text-gray-400 hover:text-gray-600">
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              <div className="rounded-lg bg-gray-50 dark:bg-navy-900 p-4">
                <pre className="text-[11px] text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                  {previewContent}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

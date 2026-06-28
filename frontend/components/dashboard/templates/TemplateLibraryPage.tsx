/**
 * TemplateLibraryPage — Enterprise CLM Template Library.
 * Grid of template cards with search, category filters, favorites, and actions.
 */

"use client";

import React, { useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search, Plus, FileText, Star, Clock, MoreHorizontal, Copy, Archive,
  Trash2, Filter, Grid3X3, List, Layers, BookOpen, FileEdit,
  ShoppingCart, Code, Shield, Briefcase, Users, Building2, FilePlus,
  ChevronDown, ExternalLink, AlertTriangle, Loader2, Package,
} from "lucide-react";
import { api } from "@/services";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";
import type {
  TemplateListItem, TemplateCategory, TemplateMetrics,
  PaginatedTemplateList, PaginatedCategoryList,
} from "./types";

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  FileLock: FileText,
  FileText: FileText,
  FileEdit: FileEdit,
  ShoppingCart: ShoppingCart,
  Code: Code,
  Shield: Shield,
  Briefcase: Briefcase,
  Users: Users,
  Building2: Building2,
  FilePlus: FilePlus,
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  under_review: "bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400",
  approved: "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400",
  deprecated: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400",
  archived: "bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400",
};

function useTemplates() {
  return useQuery<PaginatedTemplateList>({
    queryKey: ["templates"],
    queryFn: () => api.get("/templates?page_size=50"),
    staleTime: 30_000,
  });
}

function useCategories() {
  return useQuery<PaginatedCategoryList>({
    queryKey: ["template-categories"],
    queryFn: () => api.get("/templates/categories"),
    staleTime: 60_000,
  });
}

function useTemplateMetrics() {
  return useQuery<TemplateMetrics>({
    queryKey: ["template-metrics"],
    queryFn: () => api.get("/templates/metrics"),
    staleTime: 60_000,
  });
}

export default function TemplateLibraryPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const { data: templatesData, isLoading, error, refetch } = useTemplates();
  const { data: categoriesData } = useCategories();
  const { data: metrics } = useTemplateMetrics();

  const toggleFavMut = useMutation({
    mutationFn: (id: string) => api.post(`/templates/${id}/favorite`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
  });

  const duplicateMut = useMutation({
    mutationFn: (id: string) => api.post(`/templates/${id}/duplicate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
  });

  const archiveMut = useMutation({
    mutationFn: (id: string) => api.post(`/templates/${id}/archive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/templates/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
  });

  const [actionMenu, setActionMenu] = useState<string | null>(null);

  const categories = categoriesData?.data ?? [];
  const templates = templatesData?.data ?? [];

  const filteredTemplates = useMemo(() => {
    return templates.filter((t) => {
      if (search && !t.name.toLowerCase().includes(search.toLowerCase()) &&
          !(t.description || "").toLowerCase().includes(search.toLowerCase())) {
        return false;
      }
      if (categoryFilter !== "all" && t.category_id !== categoryFilter) return false;
      if (statusFilter !== "all" && t.status !== statusFilter) return false;
      return true;
    });
  }, [templates, search, categoryFilter, statusFilter]);

  const handleUseTemplate = useCallback((templateId: string) => {
    router.push(`/templates/${templateId}/generate`);
  }, [router]);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Template Library</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {metrics?.total_templates ?? 0} templates · {metrics?.approved_templates ?? 0} approved · {metrics?.generated_this_month ?? 0} generated this month
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/templates/packages")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-navy-600 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
          >
            <Package className="h-4 w-4" />
            Packages
          </button>
          <button
            onClick={() => router.push("/templates/clauses")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-navy-600 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
          >
            <BookOpen className="h-4 w-4" />
            Clause Library
          </button>
          <button
            onClick={() => router.push("/templates/new")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-navy-700 px-3 py-2 text-sm font-medium text-white hover:bg-navy-800 transition-colors shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New Template
          </button>
        </div>
      </div>

      {/* Metrics Bar */}
      {metrics && (
        <div className="grid grid-cols-4 gap-3">
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-white dark:bg-navy-800">
            <p className="text-[9px] font-semibold text-gray-500 uppercase">Total</p>
            <p className="text-xl font-bold text-navy-900 dark:text-white mt-1">{metrics.total_templates}</p>
          </div>
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-white dark:bg-navy-800">
            <p className="text-[9px] font-semibold text-gray-500 uppercase">Approved</p>
            <p className="text-xl font-bold text-green-600 mt-1">{metrics.approved_templates}</p>
          </div>
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-white dark:bg-navy-800">
            <p className="text-[9px] font-semibold text-gray-500 uppercase">Generated (Month)</p>
            <p className="text-xl font-bold text-blue-600 mt-1">{metrics.generated_this_month}</p>
          </div>
          <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-3 bg-white dark:bg-navy-800">
            <p className="text-[9px] font-semibold text-gray-500 uppercase">Categories</p>
            <p className="text-xl font-bold text-purple-600 mt-1">{categories.length}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search templates..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-800 text-gray-900 dark:text-gray-100 focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
          />
        </div>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-800 text-gray-700 dark:text-gray-300"
        >
          <option value="all">All Categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name} ({c.template_count})</option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-800 text-gray-700 dark:text-gray-300"
        >
          <option value="all">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="under_review">Under Review</option>
          <option value="approved">Approved</option>
          <option value="deprecated">Deprecated</option>
          <option value="archived">Archived</option>
        </select>

        <div className="flex items-center border border-gray-200 dark:border-navy-600 rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode("grid")}
            className={`p-2 ${viewMode === "grid" ? "bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white" : "text-gray-400 hover:text-gray-600"}`}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`p-2 ${viewMode === "list" ? "bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white" : "text-gray-400 hover:text-gray-600"}`}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Template List */}
      <AsyncBoundary
        isLoading={isLoading}
        error={error}
        isEmpty={filteredTemplates.length === 0}
        emptyMessage="No templates found"
        emptyDescription={search || categoryFilter !== "all" ? "Try adjusting your filters" : "Create your first template to get started"}
        emptyIcon={<FileText className="h-12 w-12 text-gray-300" />}
        loadingSkeleton={<CardSkeleton count={6} columns={3} />}
        onRetry={() => refetch()}
      >
        {viewMode === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTemplates.map((t) => (
              <TemplateCard
                key={t.id}
                template={t}
                categories={categories}
                onUse={() => handleUseTemplate(t.id)}
                onToggleFav={() => toggleFavMut.mutate(t.id)}
                onDuplicate={() => duplicateMut.mutate(t.id)}
                onArchive={() => archiveMut.mutate(t.id)}
                onDelete={() => { if (confirm("Delete this template?")) deleteMut.mutate(t.id); }}
                actionMenu={actionMenu}
                setActionMenu={setActionMenu}
              />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTemplates.map((t) => (
              <TemplateRow
                key={t.id}
                template={t}
                categories={categories}
                onUse={() => handleUseTemplate(t.id)}
                onToggleFav={() => toggleFavMut.mutate(t.id)}
                onDuplicate={() => duplicateMut.mutate(t.id)}
                onArchive={() => archiveMut.mutate(t.id)}
                onDelete={() => { if (confirm("Delete this template?")) deleteMut.mutate(t.id); }}
              />
            ))}
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}

// ── Template Card (Grid) ──────────────────────────────────────────

function TemplateCard({
  template: t, categories, onUse, onToggleFav, onDuplicate, onArchive, onDelete,
  actionMenu, setActionMenu,
}: {
  template: TemplateListItem;
  categories: TemplateCategory[];
  onUse: () => void;
  onToggleFav: () => void;
  onDuplicate: () => void;
  onArchive: () => void;
  onDelete: () => void;
  actionMenu: string | null;
  setActionMenu: (id: string | null) => void;
}) {
  const cat = categories.find((c) => c.id === t.category_id);
  const Icon = CATEGORY_ICONS[cat?.icon ?? "FileText"] || FileText;
  const statusColor = STATUS_COLORS[t.status] || "bg-gray-100 text-gray-600";

  return (
    <div className="rounded-xl border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 p-4 hover:shadow-md transition-shadow relative group">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-navy-50 dark:bg-navy-700 flex items-center justify-center">
            <Icon className="w-4 h-4 text-navy-600 dark:text-navy-300" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-navy-900 dark:text-white leading-tight">{t.name}</h3>
            {cat && <p className="text-[10px] text-gray-500">{cat.name}</p>}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={(e) => { e.stopPropagation(); onToggleFav(); }}
            className={`p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 ${t.is_favorite ? "text-yellow-500" : "text-gray-300"}`}>
            <Star className="w-3.5 h-3.5" fill={t.is_favorite ? "currentColor" : "none"} />
          </button>
          <div className="relative">
            <button onClick={(e) => { e.stopPropagation(); setActionMenu(actionMenu === t.id ? null : t.id); }}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400">
              <MoreHorizontal className="w-3.5 h-3.5" />
            </button>
            {actionMenu === t.id && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setActionMenu(null)} />
                <div className="absolute right-0 top-full mt-1 z-20 w-40 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-lg shadow-lg py-1">
                  <button onClick={() => { onDuplicate(); setActionMenu(null); }}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700">
                    <Copy className="w-3 h-3" /> Duplicate
                  </button>
                  <button onClick={() => { onArchive(); setActionMenu(null); }}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-navy-700">
                    <Archive className="w-3 h-3" /> Archive
                  </button>
                  <button onClick={() => { onDelete(); setActionMenu(null); }}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20">
                    <Trash2 className="w-3 h-3" /> Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Description */}
      {t.description && (
        <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">{t.description}</p>
      )}

      {/* Tags */}
      {t.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {t.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-[8px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400">
              {tag}
            </span>
          ))}
          {t.tags.length > 3 && (
            <span className="text-[8px] text-gray-400">+{t.tags.length - 3}</span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-navy-700">
        <div className="flex items-center gap-2 text-[9px] text-gray-400">
          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full ${statusColor}`}>
            {t.status.replace(/_/g, " ")}
          </span>
          {t.current_version_number && <span>v{t.current_version_number}</span>}
          <span><Clock className="w-2.5 h-2.5 inline" /> {t.usage_count} uses</span>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onUse(); }}
          disabled={t.status !== "approved"}
          className={`text-[10px] font-medium px-2 py-1 rounded-md ${
            t.status === "approved"
              ? "bg-navy-600 text-white hover:bg-navy-700"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
          } transition-colors`}
        >
          Use Template
        </button>
      </div>
    </div>
  );
}

// ── Template Row (List) ───────────────────────────────────────────

function TemplateRow({
  template: t, categories, onUse, onToggleFav, onDuplicate, onArchive, onDelete,
}: {
  template: TemplateListItem;
  categories: TemplateCategory[];
  onUse: () => void;
  onToggleFav: () => void;
  onDuplicate: () => void;
  onArchive: () => void;
  onDelete: () => void;
}) {
  const cat = categories.find((c) => c.id === t.category_id);
  const Icon = CATEGORY_ICONS[cat?.icon ?? "FileText"] || FileText;
  const statusColor = STATUS_COLORS[t.status] || "bg-gray-100 text-gray-600";

  return (
    <div className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors">
      <button onClick={onToggleFav} className={`p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 ${t.is_favorite ? "text-yellow-500" : "text-gray-300"}`}>
        <Star className="w-3.5 h-3.5" fill={t.is_favorite ? "currentColor" : "none"} />
      </button>
      <div className="w-8 h-8 rounded-lg bg-navy-50 dark:bg-navy-700 flex items-center justify-center flex-shrink-0">
        <Icon className="w-4 h-4 text-navy-600 dark:text-navy-300" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-navy-900 dark:text-white truncate">{t.name}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${statusColor}`}>{t.status.replace(/_/g, " ")}</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
          {cat && <span>{cat.name}</span>}
          {t.current_version_number && <span>· v{t.current_version_number}</span>}
          <span>· {t.usage_count} uses</span>
          {t.owner && <span>· {t.owner}</span>}
        </div>
      </div>
      <div className="flex items-center gap-1">
        <button onClick={onDuplicate} className="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700">
          <Copy className="w-3.5 h-3.5" />
        </button>
        <button onClick={onArchive} className="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700">
          <Archive className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onUse}
          disabled={t.status !== "approved"}
          className={`text-[10px] font-medium px-2.5 py-1.5 rounded-md ${
            t.status === "approved"
              ? "bg-navy-600 text-white hover:bg-navy-700"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
          } transition-colors`}
        >
          Use Template
        </button>
      </div>
    </div>
  );
}

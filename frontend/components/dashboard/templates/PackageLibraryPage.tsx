/**
 * PackageLibraryPage — Browse, create, and manage template packages.
 *
 * A package is a curated collection of templates for a specific industry or use case.
 * Examples: Procurement Pack (MSA, NDA, SOW, Supplier Code of Conduct, DPA)
 */

"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus, Search, Loader2, Package, FileText, Building2, CheckCircle2,
  XCircle, Globe, Tag, Layers, BookOpen, AlertTriangle, Trash2,
  Edit3, Eye, Archive, ExternalLink,
} from "lucide-react";
import { api } from "@/services";
import type {
  TemplatePackage, TemplatePackageCreate, PackageItemCreate,
  PaginatedPackageList,
} from "./types";

const INDUSTRIES = [
  "procurement", "healthcare", "banking", "saas",
  "manufacturing", "real_estate", "energy", "insurance",
];

const INDUSTRY_LABELS: Record<string, string> = {
  procurement: "Procurement",
  healthcare: "Healthcare",
  banking: "Banking",
  saas: "SaaS",
  manufacturing: "Manufacturing",
  real_estate: "Real Estate",
  energy: "Energy",
  insurance: "Insurance",
};

interface PackageFormData {
  name: string;
  industry: string;
  description: string;
  tags: string;
  icon: string;
}

const emptyForm: PackageFormData = {
  name: "",
  industry: "",
  description: "",
  tags: "",
  icon: "Package",
};

export default function PackageLibraryPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [industryFilter, setIndustryFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingPkg, setEditingPkg] = useState<TemplatePackage | null>(null);
  const [form, setForm] = useState<PackageFormData>(emptyForm);
  const [formError, setFormError] = useState("");
  const [viewingPkg, setViewingPkg] = useState<TemplatePackage | null>(null);

  // ── Queries ──────────────────────────────────────────────────

  const { data: packagesData, isLoading } = useQuery<PaginatedPackageList>({
    queryKey: ["packages", search, industryFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (industryFilter) params.set("industry", industryFilter);
      if (search) params.set("search", search);
      return api.get(`/templates/packages?${params.toString()}`);
    },
    staleTime: 15_000,
  });

  const { data: allTemplates } = useQuery<{ data: Array<{ id: string; name: string }> }>({
    queryKey: ["templates-list"],
    queryFn: () => api.get("/templates?page_size=100"),
    staleTime: 30_000,
  });

  // ── Mutations ────────────────────────────────────────────────

  const createMut = useMutation({
    mutationFn: (data: TemplatePackageCreate) => api.post("/templates/packages", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["packages"] });
      resetForm();
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<TemplatePackageCreate> }) =>
      api.put(`/templates/packages/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["packages"] });
      resetForm();
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/templates/packages/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["packages"] }),
  });

  const publishMut = useMutation({
    mutationFn: (id: string) => api.post(`/templates/packages/${id}/publish`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["packages"] }),
  });

  // ── Helpers ──────────────────────────────────────────────────

  const resetForm = () => {
    setForm(emptyForm);
    setShowForm(false);
    setEditingPkg(null);
    setFormError("");
  };

  const openEdit = (pkg: TemplatePackage) => {
    setEditingPkg(pkg);
    setForm({
      name: pkg.name,
      industry: pkg.industry || "",
      description: pkg.description || "",
      tags: (pkg.tags || []).join(", "),
      icon: pkg.icon || "Package",
    });
    setShowForm(true);
    setFormError("");
  };

  const handleSave = async () => {
    if (!form.name.trim()) { setFormError("Package name is required"); return; }

    const payload: TemplatePackageCreate = {
      name: form.name,
      industry: form.industry || null,
      description: form.description || null,
      tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
      icon: form.icon || null,
    };

    if (editingPkg) {
      updateMut.mutate({ id: editingPkg.id, data: payload });
    } else {
      createMut.mutate(payload);
    }
  };

  const packages = packagesData?.data ?? [];
  const templates = allTemplates?.data ?? [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy-900 dark:text-white">Template Packages</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Curated collections of templates — industry starter packs, tenant onboarding, demo environments
          </p>
        </div>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800"
        >
          <Plus className="w-4 h-4" /> New Package
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search packages..."
            className="w-full pl-8 pr-3 py-2 text-xs border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
          />
        </div>
        <select
          value={industryFilter}
          onChange={(e) => setIndustryFilter(e.target.value)}
          className="px-3 py-2 text-xs border border-gray-200 rounded-lg focus:border-navy-400"
        >
          <option value="">All Industries</option>
          {INDUSTRIES.map((ind) => (
            <option key={ind} value={ind}>{INDUSTRY_LABELS[ind] || ind}</option>
          ))}
        </select>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase">
              {editingPkg ? "Edit Package" : "New Package"}
            </h3>
            <button onClick={resetForm} className="text-gray-400 hover:text-gray-600">
              <XCircle className="w-4 h-4" />
            </button>
          </div>
          {formError && (
            <div className="flex items-center gap-2 p-2 mb-3 rounded bg-red-50 text-red-600 text-[10px]">
              <AlertTriangle className="w-3 h-3" /> {formError}
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-medium text-gray-600">Name *</label>
                <input type="text" value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400"
                  placeholder="Procurement Package" />
              </div>
              <div>
                <label className="text-[10px] font-medium text-gray-600">Industry</label>
                <select value={form.industry}
                  onChange={(e) => setForm({ ...form, industry: e.target.value })}
                  className="w-full mt-1 px-3 py-2 text-xs border border-gray-200 rounded-lg">
                  <option value="">General</option>
                  {INDUSTRIES.map((ind) => (
                    <option key={ind} value={ind}>{INDUSTRY_LABELS[ind]}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-medium text-gray-600">Tags (comma separated)</label>
                <input type="text" value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                  className="w-full mt-1 px-3 py-2 text-xs border border-gray-200 rounded-lg"
                  placeholder="onboarding, essential, standard" />
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-medium text-gray-600">Description</label>
                <textarea value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={4}
                  className="w-full mt-1 px-3 py-2 text-xs border border-gray-200 rounded-lg focus:border-navy-400"
                  placeholder="Complete set of procurement templates for vendor onboarding..." />
              </div>
              <button
                onClick={handleSave}
                disabled={createMut.isPending || updateMut.isPending}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50"
              >
                {(createMut.isPending || updateMut.isPending) ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-3 h-3" />
                )}
                {editingPkg ? "Update Package" : "Create Package"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Package List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : packages.length === 0 ? (
        <div className="text-center py-12">
          <Package className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-500">No packages found</p>
          <p className="text-xs text-gray-400 mt-1">
            {search ? "Try a different search term" : "Create your first template package"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {packages.map((pkg) => (
            <div
              key={pkg.id}
              className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Package className="w-4 h-4 text-navy-500" />
                    <h3 className="text-sm font-medium text-navy-900 dark:text-white">{pkg.name}</h3>
                    {pkg.is_published && (
                      <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">
                        Published
                      </span>
                    )}
                    {!pkg.is_published && (
                      <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                        Draft
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    {pkg.industry && (
                      <span className="text-[9px] flex items-center gap-1 text-gray-500">
                        <Building2 className="w-3 h-3" />
                        {INDUSTRY_LABELS[pkg.industry] || pkg.industry}
                      </span>
                    )}
                    <span className="text-[9px] flex items-center gap-1 text-gray-500">
                      <FileText className="w-3 h-3" />
                      {pkg.template_count} templates
                    </span>
                    <span className="text-[9px] text-gray-400">v{pkg.version}</span>
                  </div>
                  {pkg.description && (
                    <p className="text-[10px] text-gray-600 dark:text-gray-400 mt-2 line-clamp-2">
                      {pkg.description}
                    </p>
                  )}
                  {pkg.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {pkg.tags.map((tag) => (
                        <span key={tag} className="text-[8px] px-1.5 py-0.5 rounded-full bg-navy-50 text-navy-600 dark:bg-navy-700 dark:text-navy-300">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {/* Items list */}
                  {pkg.items.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-100 dark:border-navy-700">
                      <p className="text-[9px] font-medium text-gray-500 mb-1">Templates:</p>
                      <div className="space-y-1">
                        {pkg.items.map((item) => (
                          <div key={item.id} className="flex items-center gap-1.5 text-[9px] text-gray-600">
                            <FileText className="w-3 h-3 text-gray-400" />
                            <span>{item.template_name || item.template_id}</span>
                            {item.is_required && (
                              <span className="text-[7px] px-1 py-0.5 rounded bg-blue-50 text-blue-600">Required</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1 ml-4">
                  {!pkg.is_published && (
                    <button
                      onClick={() => publishMut.mutate(pkg.id)}
                      className="p-1.5 rounded hover:bg-green-50 text-green-500"
                      title="Publish"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                  <button
                    onClick={() => setViewingPkg(pkg)}
                    className="p-1.5 rounded hover:bg-gray-100 text-gray-400"
                    title="View"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => openEdit(pkg)}
                    className="p-1.5 rounded hover:bg-gray-100 text-gray-400"
                    title="Edit"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete package "${pkg.name}"?`)) deleteMut.mutate(pkg.id);
                    }}
                    className="p-1.5 rounded hover:bg-red-50 text-red-400"
                    title="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* View Package Modal */}
      {viewingPkg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setViewingPkg(null)}>
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Package className="w-5 h-5 text-navy-500" />
                  <h2 className="text-lg font-bold text-navy-900 dark:text-white">{viewingPkg.name}</h2>
                </div>
                <button onClick={() => setViewingPkg(null)} className="text-gray-400 hover:text-gray-600">
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              <div className="flex items-center gap-2">
                {viewingPkg.industry && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-700 dark:text-navy-200">
                    <Building2 className="w-3 h-3 inline mr-1" />
                    {INDUSTRY_LABELS[viewingPkg.industry] || viewingPkg.industry}
                  </span>
                )}
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                  v{viewingPkg.version}
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                  viewingPkg.is_published ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                }`}>
                  {viewingPkg.is_published ? "Published" : "Draft"}
                </span>
              </div>
              {viewingPkg.description && (
                <p className="text-xs text-gray-600 dark:text-gray-400">{viewingPkg.description}</p>
              )}
              {viewingPkg.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {viewingPkg.tags.map((tag) => (
                    <span key={tag} className="text-[9px] px-2 py-0.5 rounded-full bg-navy-50 text-navy-600 dark:bg-navy-700 dark:text-navy-300">{tag}</span>
                  ))}
                </div>
              )}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Templates ({viewingPkg.items.length})</h3>
                {viewingPkg.items.length === 0 ? (
                  <p className="text-[10px] text-gray-400 italic">No templates in this package yet</p>
                ) : (
                  <div className="space-y-2">
                    {viewingPkg.items.map((item) => (
                      <div key={item.id} className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-navy-900">
                        <div className="flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5 text-gray-400" />
                          <span className="text-[11px] font-medium text-navy-900 dark:text-white">
                            {item.template_name || item.template_id}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {item.is_required && (
                            <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-600">Required</span>
                          )}
                          {item.template_status && (
                            <span className="text-[8px] text-gray-400">{item.template_status}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-3 text-[9px] text-gray-400 pt-2 border-t border-gray-100">
                <span>Created by {viewingPkg.created_by}</span>
                {viewingPkg.updated_at && (
                  <span>Updated {new Date(viewingPkg.updated_at).toLocaleDateString()}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

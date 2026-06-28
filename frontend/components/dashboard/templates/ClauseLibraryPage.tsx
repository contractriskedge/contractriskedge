/**
 * ClauseLibraryPage — Browse, create, edit, and manage reusable clauses.
 * Supports the full approval workflow: draft → legal_review → approved → published.
 */

"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus, Search, Loader2, AlertTriangle, FileText, Tag, Shield,
  CheckCircle2, XCircle, Clock, ArrowUpDown, BookOpen, GitBranch,
  BarChart3, Trash2, Edit3, Eye, Send, Check, X, Archive,
} from "lucide-react";
import { api } from "@/services";
import type {
  TemplateClause, TemplateClauseCreate, ClauseAnalytics,
  ClauseDependencyInfo, PaginatedClauseList,
} from "./types";

const CLAUSE_TYPES = [
  "payment", "confidentiality", "liability", "governing_law",
  "termination", "indemnification", "insurance", "warranty",
  "dispute_resolution", "force_majeure", "assignment", "waiver",
  "notice", "entire_agreement", "amendment", "signature",
  "recitals", "definitions", "general", "other",
];

const RISK_LEVELS = [
  { value: "critical", label: "Critical", color: "bg-red-100 text-red-700" },
  { value: "high", label: "High", color: "bg-orange-100 text-orange-700" },
  { value: "medium", label: "Medium", color: "bg-yellow-100 text-yellow-700" },
  { value: "low", label: "Low", color: "bg-green-100 text-green-700" },
];

const STATUS_BADGES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  legal_review: "bg-blue-100 text-blue-600",
  approved: "bg-green-100 text-green-700",
  published: "bg-emerald-100 text-emerald-700",
  deprecated: "bg-yellow-100 text-yellow-700",
  archived: "bg-red-100 text-red-600",
};

interface ClauseFormData {
  clause_type: string;
  title: string;
  content: string;
  category: string;
  risk_level: string;
  ai_rewrite_allowed: boolean;
  is_required: boolean;
  is_conditional: boolean;
  condition_expression: string;
  change_summary: string;
  tags: string;
}

const emptyForm: ClauseFormData = {
  clause_type: "general",
  title: "",
  content: "",
  category: "",
  risk_level: "medium",
  ai_rewrite_allowed: false,
  is_required: false,
  is_conditional: false,
  condition_expression: "",
  change_summary: "",
  tags: "",
};

export default function ClauseLibraryPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingClause, setEditingClause] = useState<TemplateClause | null>(null);
  const [form, setForm] = useState<ClauseFormData>(emptyForm);
  const [formError, setFormError] = useState("");
  const [viewingClause, setViewingClause] = useState<TemplateClause | null>(null);
  const [depsClause, setDepsClause] = useState<ClauseDependencyInfo | null>(null);
  const [showDeps, setShowDeps] = useState(false);
  const [tab, setTab] = useState<"browse" | "analytics">("browse");

  // ── Queries ──────────────────────────────────────────────────

  const { data: clausesData, isLoading } = useQuery<PaginatedClauseList>({
    queryKey: ["clauses", search, typeFilter, statusFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (search) params.set("q", search);
      if (typeFilter) params.set("clause_type", typeFilter);
      const qs = params.toString();
      const path = search
        ? `/templates/clauses/search?${qs}`
        : qs ? `/templates/clauses?${qs}` : `/templates/clauses`;
      return api.get(path);
    },
    staleTime: 15_000,
  });

  const { data: analytics } = useQuery<ClauseAnalytics>({
    queryKey: ["clause-analytics"],
    queryFn: () => api.get("/templates/clauses/analytics"),
    staleTime: 30_000,
    enabled: tab === "analytics",
  });

  // ── Mutations ────────────────────────────────────────────────

  const createMut = useMutation({
    mutationFn: (data: TemplateClauseCreate) => api.post("/templates/clauses", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clauses"] });
      queryClient.invalidateQueries({ queryKey: ["clause-analytics"] });
      resetForm();
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<TemplateClauseCreate> }) =>
      api.put(`/templates/clauses/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clauses"] });
      queryClient.invalidateQueries({ queryKey: ["clause-analytics"] });
      resetForm();
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/templates/clauses/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clauses"] });
      queryClient.invalidateQueries({ queryKey: ["clause-analytics"] });
    },
  });

  const submitMut = useMutation({
    mutationFn: (id: string) => api.post(`/templates/clauses/${id}/submit`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clauses"] }),
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => api.post(`/templates/clauses/${id}/approve`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clauses"] }),
  });

  const publishMut = useMutation({
    mutationFn: (id: string) => api.post(`/templates/clauses/${id}/publish`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clauses"] }),
  });

  const rejectMut = useMutation({
    mutationFn: (id: string) => api.post(`/templates/clauses/${id}/reject?reason=Returned+to+draft`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clauses"] }),
  });

  // ── Helpers ──────────────────────────────────────────────────

  const resetForm = () => {
    setForm(emptyForm);
    setShowForm(false);
    setEditingClause(null);
    setFormError("");
  };

  const openEdit = (clause: TemplateClause) => {
    setEditingClause(clause);
    setForm({
      clause_type: clause.clause_type,
      title: clause.title,
      content: clause.content,
      category: clause.category || "",
      risk_level: clause.risk_level || "medium",
      ai_rewrite_allowed: clause.ai_rewrite_allowed,
      is_required: clause.is_required,
      is_conditional: clause.is_conditional,
      condition_expression: clause.condition_expression || "",
      change_summary: "",
      tags: (clause.tags || []).join(", "),
    });
    setShowForm(true);
    setFormError("");
  };

  const handleSave = async () => {
    if (!form.title.trim()) { setFormError("Title is required"); return; }
    if (!form.content.trim()) { setFormError("Content is required"); return; }

    const payload: TemplateClauseCreate = {
      clause_type: form.clause_type,
      title: form.title,
      content: form.content,
      category: form.category || null,
      risk_level: form.risk_level || null,
      ai_rewrite_allowed: form.ai_rewrite_allowed,
      is_required: form.is_required,
      is_conditional: form.is_conditional,
      condition_expression: form.condition_expression || null,
      change_summary: form.change_summary || null,
      tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
    };

    if (editingClause) {
      updateMut.mutate({ id: editingClause.id, data: payload });
    } else {
      createMut.mutate(payload);
    }
  };

  const loadDeps = async (clause: TemplateClause) => {
    try {
      const data = await api.get<ClauseDependencyInfo>(`/templates/clauses/${clause.id}/dependencies`);
      setDepsClause(data);
      setShowDeps(true);
    } catch {
      setDepsClause(null);
      setShowDeps(true);
    }
  };

  const clauses = clausesData?.data ?? [];
  const riskColor = (level?: string | null) =>
    RISK_LEVELS.find((r) => r.value === level)?.color ?? "bg-gray-100 text-gray-600";

  // ── Render ───────────────────────────────────────────────────

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy-900 dark:text-white">Clause Library</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Reusable contract clauses with versioning, approval workflow, and dependency tracking
          </p>
        </div>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800"
        >
          <Plus className="w-4 h-4" /> New Clause
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-navy-700">
        <button
          onClick={() => setTab("browse")}
          className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
            tab === "browse"
              ? "border-navy-700 text-navy-900 dark:text-white"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <BookOpen className="w-3.5 h-3.5 inline mr-1" /> Browse
        </button>
        <button
          onClick={() => setTab("analytics")}
          className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
            tab === "analytics"
              ? "border-navy-700 text-navy-900 dark:text-white"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5 inline mr-1" /> Analytics
        </button>
      </div>

      {tab === "analytics" ? (
        /* ════════════════ ANALYTICS TAB ════════════════ */
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <p className="text-[10px] text-gray-500 uppercase">Total Clauses</p>
              <p className="text-2xl font-bold text-navy-900 dark:text-white mt-1">{analytics?.total_clauses ?? 0}</p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <p className="text-[10px] text-gray-500 uppercase">Published</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{analytics?.published_clauses ?? 0}</p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <p className="text-[10px] text-gray-500 uppercase">Draft</p>
              <p className="text-2xl font-bold text-gray-500 mt-1">{analytics?.draft_clauses ?? 0}</p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <p className="text-[10px] text-gray-500 uppercase">AI Rewrite Rate</p>
              <p className="text-2xl font-bold text-blue-600 mt-1">{analytics?.avg_ai_rewrite_rate ?? 0}%</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Most Used Clauses */}
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Most Used Clauses</h3>
              {(!analytics?.most_used_clauses || analytics.most_used_clauses.length === 0) ? (
                <p className="text-[10px] text-gray-400 italic">No clauses used yet</p>
              ) : (
                <div className="space-y-2">
                  {analytics.most_used_clauses.slice(0, 5).map((c) => (
                    <div key={c.id} className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-navy-900">
                      <div className="flex items-center gap-2">
                        <FileText className="w-3 h-3 text-gray-400" />
                        <span className="text-[11px] font-medium text-navy-900 dark:text-white">{c.title}</span>
                      </div>
                      <span className="text-[10px] text-gray-500">{c.usage_count} uses</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Highest Risk Clauses */}
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Highest Risk Clauses</h3>
              {(!analytics?.highest_risk_clauses || analytics.highest_risk_clauses.length === 0) ? (
                <p className="text-[10px] text-gray-400 italic">No high risk clauses</p>
              ) : (
                <div className="space-y-2">
                  {analytics.highest_risk_clauses.slice(0, 5).map((c) => (
                    <div key={c.id} className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-navy-900">
                      <div className="flex items-center gap-2">
                        <Shield className="w-3 h-3 text-red-400" />
                        <span className="text-[11px] font-medium text-navy-900 dark:text-white">{c.title}</span>
                      </div>
                      <span className={`text-[8px] px-1.5 py-0.5 rounded-full ${riskColor(c.risk_level)}`}>
                        {c.risk_level}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Deprecated Still In Use */}
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Deprecated — Still In Use</h3>
              {(!analytics?.deprecated_still_used || analytics.deprecated_still_used.length === 0) ? (
                <p className="text-[10px] text-gray-400 italic">No deprecated clauses in use</p>
              ) : (
                <div className="space-y-2">
                  {analytics.deprecated_still_used.slice(0, 5).map((c) => (
                    <div key={c.id} className="flex items-center justify-between p-2 rounded bg-yellow-50 dark:bg-navy-900">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-3 h-3 text-yellow-500" />
                        <span className="text-[11px] font-medium text-navy-900 dark:text-white">{c.title}</span>
                      </div>
                      <span className="text-[10px] text-yellow-600">{c.usage_count} uses</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Clauses by Type */}
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Clauses by Type</h3>
              {(!analytics?.clauses_by_type || analytics.clauses_by_type.length === 0) ? (
                <p className="text-[10px] text-gray-400 italic">No data</p>
              ) : (
                <div className="space-y-1.5">
                  {analytics.clauses_by_type.map((item) => (
                    <div key={item.type} className="flex items-center gap-2">
                      <span className="text-[10px] text-gray-600 w-28 truncate">{item.type.replace(/_/g, " ")}</span>
                      <div className="flex-1 h-3 rounded-full bg-gray-100 dark:bg-navy-700 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-navy-500"
                          style={{ width: `${Math.min(100, (item.count / (analytics.total_clauses || 1)) * 100)}%` }}
                        />
                      </div>
                      <span className="text-[9px] text-gray-500 w-6 text-right">{item.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* ════════════════ BROWSE TAB ════════════════ */
        <>
          {/* Filters */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search clauses..."
                className="w-full pl-8 pr-3 py-2 text-xs border border-gray-200 rounded-lg focus:border-navy-400 focus:ring-1 focus:ring-navy-400"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-3 py-2 text-xs border border-gray-200 rounded-lg focus:border-navy-400"
            >
              <option value="">All Types</option>
              {CLAUSE_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>

          {/* Clause Form (Create/Edit) */}
          {showForm && (
            <div className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-500 uppercase">
                  {editingClause ? "Edit Clause" : "New Clause"}
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
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2 space-y-3">
                  <div>
                    <label className="text-[10px] font-medium text-gray-600">Title *</label>
                    <input
                      type="text" value={form.title}
                      onChange={(e) => setForm({ ...form, title: e.target.value })}
                      className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400"
                      placeholder="Limitation of Liability"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium text-gray-600">Content *</label>
                    <textarea
                      value={form.content}
                      onChange={(e) => setForm({ ...form, content: e.target.value })}
                      rows={8}
                      className="w-full mt-1 px-3 py-2 text-[11px] font-mono border border-gray-200 rounded-lg focus:border-navy-400 bg-gray-50"
                      placeholder="Neither party shall be liable to the other for any indirect, incidental, special, or consequential damages..."
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium text-gray-600">Change Summary</label>
                    <input
                      type="text" value={form.change_summary}
                      onChange={(e) => setForm({ ...form, change_summary: e.target.value })}
                      className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-navy-400"
                      placeholder="Updated liability cap from $1M to $2M"
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] font-medium text-gray-600">Clause Type</label>
                    <select
                      value={form.clause_type}
                      onChange={(e) => setForm({ ...form, clause_type: e.target.value })}
                      className="w-full mt-1 px-3 py-2 text-xs border border-gray-200 rounded-lg"
                    >
                      {CLAUSE_TYPES.map((t) => (
                        <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] font-medium text-gray-600">Risk Level</label>
                    <select
                      value={form.risk_level}
                      onChange={(e) => setForm({ ...form, risk_level: e.target.value })}
                      className="w-full mt-1 px-3 py-2 text-xs border border-gray-200 rounded-lg"
                    >
                      {RISK_LEVELS.map((r) => (
                        <option key={r.value} value={r.value}>{r.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] font-medium text-gray-600">Category</label>
                    <input
                      type="text" value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value })}
                      className="w-full mt-1 px-3 py-2 text-xs border border-gray-200 rounded-lg"
                      placeholder="e.g. Procurement"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium text-gray-600">Tags (comma separated)</label>
                    <input
                      type="text" value={form.tags}
                      onChange={(e) => setForm({ ...form, tags: e.target.value })}
                      className="w-full mt-1 px-3 py-2 text-xs border border-gray-200 rounded-lg"
                      placeholder="liability, cap, standard"
                    />
                  </div>
                  <div className="space-y-2 pt-2 border-t border-gray-100">
                    <label className="flex items-center gap-2 text-[10px] text-gray-600">
                      <input
                        type="checkbox" checked={form.ai_rewrite_allowed}
                        onChange={(e) => setForm({ ...form, ai_rewrite_allowed: e.target.checked })}
                      />
                      Allow AI Rewrite
                    </label>
                    <label className="flex items-center gap-2 text-[10px] text-gray-600">
                      <input
                        type="checkbox" checked={form.is_required}
                        onChange={(e) => setForm({ ...form, is_required: e.target.checked })}
                      />
                      Required in all templates
                    </label>
                    <label className="flex items-center gap-2 text-[10px] text-gray-600">
                      <input
                        type="checkbox" checked={form.is_conditional}
                        onChange={(e) => setForm({ ...form, is_conditional: e.target.checked })}
                      />
                      Conditional
                    </label>
                    {form.is_conditional && (
                      <input
                        type="text" value={form.condition_expression}
                        onChange={(e) => setForm({ ...form, condition_expression: e.target.value })}
                        className="w-full px-2 py-1 text-[9px] font-mono border border-gray-200 rounded"
                        placeholder='e.g. Country == "Germany"'
                      />
                    )}
                  </div>
                  <button
                    onClick={handleSave}
                    disabled={createMut.isPending || updateMut.isPending}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 disabled:opacity-50"
                  >
                    {(createMut.isPending || updateMut.isPending) ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Check className="w-3 h-3" />
                    )}
                    {editingClause ? "Update Clause" : "Create Clause"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Clause List */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : clauses.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-500">No clauses found</p>
              <p className="text-xs text-gray-400 mt-1">
                {search ? "Try a different search term" : "Create your first reusable clause"}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {clauses.map((clause) => (
                <div
                  key={clause.id}
                  className="rounded-lg border border-gray-200 dark:border-navy-700 p-4 bg-white dark:bg-navy-800 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-medium text-navy-900 dark:text-white">{clause.title}</h3>
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full ${riskColor(clause.risk_level)}`}>
                          {clause.risk_level || "unspecified"}
                        </span>
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full ${STATUS_BADGES[clause.status] || "bg-gray-100 text-gray-600"}`}>
                          {clause.status.replace(/_/g, " ")}
                        </span>
                      </div>
                      <p className="text-[10px] text-gray-500 mt-1">
                        {clause.clause_type.replace(/_/g, " ")}
                        {clause.category ? ` · ${clause.category}` : ""}
                        {clause.version > 1 ? ` · v${clause.version}` : ""}
                      </p>
                      <p className="text-[10px] text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                        {clause.content.substring(0, 200)}...
                      </p>
                      <div className="flex items-center gap-3 mt-2 text-[9px] text-gray-400">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" /> {clause.usage_count} templates
                        </span>
                        <span className="flex items-center gap-1">
                          <Tag className="w-3 h-3" /> {(clause.tags || []).length} tags
                        </span>
                        {clause.ai_rewrite_allowed && (
                          <span className="text-blue-500">AI rewrite allowed</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 ml-4">
                      {/* Approval Workflow Actions */}
                      {clause.status === "draft" && (
                        <button
                          onClick={() => submitMut.mutate(clause.id)}
                          className="p-1.5 rounded hover:bg-blue-50 text-blue-500"
                          title="Submit for Review"
                        >
                          <Send className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {clause.status === "legal_review" && (
                        <>
                          <button
                            onClick={() => approveMut.mutate(clause.id)}
                            className="p-1.5 rounded hover:bg-green-50 text-green-500"
                            title="Approve"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => rejectMut.mutate(clause.id)}
                            className="p-1.5 rounded hover:bg-red-50 text-red-500"
                            title="Reject"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                      {clause.status === "approved" && (
                        <button
                          onClick={() => publishMut.mutate(clause.id)}
                          className="p-1.5 rounded hover:bg-emerald-50 text-emerald-500"
                          title="Publish"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => setViewingClause(clause)}
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-400"
                        title="View"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => openEdit(clause)}
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-400"
                        title="Edit"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => loadDeps(clause)}
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-400"
                        title="Dependencies"
                      >
                        <GitBranch className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Delete clause "${clause.title}"?`)) deleteMut.mutate(clause.id);
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
        </>
      )}

      {/* View Clause Modal */}
      {viewingClause && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setViewingClause(null)}>
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-navy-900 dark:text-white">{viewingClause.title}</h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {viewingClause.clause_type.replace(/_/g, " ")}
                    {viewingClause.category ? ` · ${viewingClause.category}` : ""}
                    {viewingClause.version > 1 ? ` · v${viewingClause.version}` : ""}
                  </p>
                </div>
                <button onClick={() => setViewingClause(null)} className="text-gray-400 hover:text-gray-600">
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${riskColor(viewingClause.risk_level)}`}>
                  {viewingClause.risk_level || "unspecified"} risk
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${STATUS_BADGES[viewingClause.status] || "bg-gray-100 text-gray-600"}`}>
                  {viewingClause.status.replace(/_/g, " ")}
                </span>
                {viewingClause.ai_rewrite_allowed && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-600">AI Rewrite</span>
                )}
              </div>
              <div className="rounded-lg bg-gray-50 dark:bg-navy-900 p-4">
                <pre className="text-[11px] text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                  {viewingClause.content}
                </pre>
              </div>
              {viewingClause.is_conditional && viewingClause.condition_expression && (
                <div className="flex items-center gap-2 p-2 rounded bg-yellow-50 text-yellow-700 text-[10px]">
                  <AlertTriangle className="w-3 h-3" />
                  Conditional: {viewingClause.condition_expression}
                </div>
              )}
              {viewingClause.fallback_clause_id && (
                <div className="text-[10px] text-gray-500">
                  Fallback clause: {viewingClause.fallback_clause_id}
                </div>
              )}
              <div className="flex items-center gap-4 text-[9px] text-gray-400 pt-2 border-t border-gray-100">
                <span>Usage: {viewingClause.usage_count} templates · {viewingClause.contract_usage_count} contracts</span>
                <span>Created by {viewingClause.created_by}</span>
                {viewingClause.updated_at && (
                  <span>Updated {new Date(viewingClause.updated_at).toLocaleDateString()}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dependency Modal */}
      {showDeps && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => { setShowDeps(false); setDepsClause(null); }}>
          <div className="bg-white dark:bg-navy-800 rounded-xl shadow-xl max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-navy-900 dark:text-white">Clause Dependencies</h2>
                <button onClick={() => { setShowDeps(false); setDepsClause(null); }} className="text-gray-400 hover:text-gray-600">
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              {depsClause ? (
                <div className="space-y-3">
                  <p className="text-xs text-gray-700 dark:text-gray-300 font-medium">{depsClause.clause_title}</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-gray-50 dark:bg-navy-900 text-center">
                      <p className="text-2xl font-bold text-navy-900 dark:text-white">{depsClause.template_count}</p>
                      <p className="text-[9px] text-gray-500">Templates</p>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50 dark:bg-navy-900 text-center">
                      <p className="text-2xl font-bold text-navy-900 dark:text-white">{depsClause.contract_count}</p>
                      <p className="text-[9px] text-gray-500">Contracts</p>
                    </div>
                  </div>
                  {depsClause.templates.length > 0 && (
                    <div>
                      <p className="text-[10px] font-medium text-gray-500 mb-1">Used in:</p>
                      <div className="space-y-1">
                        {depsClause.templates.map((t) => (
                          <div key={t.id} className="text-[10px] text-gray-600 flex items-center gap-1">
                            <FileText className="w-3 h-3" /> {t.name}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {depsClause.blocking_reasons.length > 0 && (
                    <div className="p-2 rounded bg-yellow-50 text-yellow-700 text-[10px]">
                      {depsClause.blocking_reasons.map((r, i) => (
                        <div key={i} className="flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> {r}</div>
                      ))}
                    </div>
                  )}
                  <p className="text-[10px] text-gray-500">
                    {depsClause.can_delete ? "This clause can be safely deleted." : "This clause is in use and cannot be deleted."}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-gray-500">Failed to load dependency data.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

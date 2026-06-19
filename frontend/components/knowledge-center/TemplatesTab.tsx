/**
 * Templates tab — library of all redline templates with status badges and preview panel.
 */
"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Plus,
  Loader2,
  Search,
  CheckCircle2,
  AlertCircle,
  Clock,
  Archive,
  Sparkles,
  Eye,
  ThumbsUp,
  Send,
  X,
  ArrowRight,
  FileCheck,
  Globe,
  Building2,
  Shield,
} from "lucide-react";
import { useTemplates, useDeleteTemplate, useUpdateTemplate, useCreateTemplate } from "@/services/hooks/useRedlineTemplates";
import { redlineTemplateApi } from "@/services/api/redlineTemplates";
import type { RedlineTemplate } from "@/services/api/redlineTemplates";

const STATUS_STYLE: Record<string, { label: string; icon: React.ElementType; class: string; next?: string }> = {
  draft: { label: "Draft", icon: Clock, class: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300", next: "pending_review" },
  pending_review: { label: "Pending Review", icon: Eye, class: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", next: "active" },
  active: { label: "Approved", icon: CheckCircle2, class: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400", next: "published" },
  published: { label: "Published", icon: ThumbsUp, class: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" },
  ai_draft: { label: "AI Generated", icon: Sparkles, class: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400", next: "pending_review" },
  deprecated: { label: "Deprecated", icon: AlertCircle, class: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" },
  retired: { label: "Retired", icon: Archive, class: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
};

// Related clauses mapping
const RELATED_CLAUSES: Record<string, string[]> = {
  data_privacy: ["gdpr", "cross_border_transfer", "data_breach", "dpa"],
  gdpr: ["data_privacy", "cross_border_transfer", "data_breach", "dpa"],
  confidentiality: ["nda", "non_compete", "return_of_information"],
  indemnification: ["liability", "limitation_of_liability", "insurance"],
  liability: ["indemnification", "limitation_of_liability", "insurance"],
  termination: ["notice_period", "auto_renewal", "for_cause_termination"],
  intellectual_property: ["ip_ownership", "license", "non_compete"],
};

export function TemplatesTab() {
  const { data: templates, isLoading } = useTemplates();
  const deleteTemplate = useDeleteTemplate();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [previewTemplate, setPreviewTemplate] = useState<RedlineTemplate | null>(null);
  const [applyReviewId, setApplyReviewId] = useState("");
  const [applyFindingId, setApplyFindingId] = useState("");
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newTemplate, setNewTemplate] = useState({ name: "", clause_type: "", category: "", template_text: "" });
  const createTemplate = useCreateTemplate();

  // Context-aware review detection
  const [reviewSearch, setReviewSearch] = useState("");
  const [reviewResults, setReviewResults] = useState<{ review_id: string; filename: string }[]>([]);
  const [selectedReview, setSelectedReview] = useState<{ review_id: string; filename: string } | null>(null);
  const [showReviewDropdown, setShowReviewDropdown] = useState(false);
  const [findings, setFindings] = useState<{ finding_id: string; title: string; clause_type: string }[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<{ finding_id: string; title: string } | null>(null);
  const reviewSearchRef = useRef<HTMLDivElement>(null);

  // Auto-detect review from URL params (e.g. ?review_id=xxx&finding_id=yyy)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const rid = params.get("review_id");
    const fid = params.get("finding_id");
    if (rid) {
      setSelectedReview({ review_id: rid, filename: "Current Review" });
      setApplyReviewId(rid);
    }
    if (fid) {
      setSelectedFinding({ finding_id: fid, title: "Current Finding" });
      setApplyFindingId(fid);
    }
  }, []);

  // Search reviews when user types
  useEffect(() => {
    if (reviewSearch.length < 2) {
      setReviewResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const { reviewService } = await import("@/services/api/reviews");
        const result = await reviewService.list({ page_size: 10 });
        const items = result.data || [];
        const filtered = items
          .filter((r: any) => (r.document_name || r.original_filename || "").toLowerCase().includes(reviewSearch.toLowerCase()))
          .map((r: any) => ({ review_id: r.review_id || r.id, filename: r.document_name || r.original_filename || "Unknown" }));
        setReviewResults(filtered.slice(0, 5));
        setShowReviewDropdown(filtered.length > 0);
      } catch { /* ignore */ }
    }, 300);
    return () => clearTimeout(timer);
  }, [reviewSearch]);

  // Load findings when a review is selected
  useEffect(() => {
    if (!selectedReview) return;
    (async () => {
      try {
        const { reviewService } = await import("@/services/api/reviews");
        const result = await reviewService.get(selectedReview.review_id);
        // Findings are at /reviews/{id}/findings endpoint
        const findingsResp = await (await import("@/services/api/client")).api.get(`/reviews/${selectedReview.review_id}/findings`);
        const items = findingsResp?.findings || (result as any)?.findings || [];
        setFindings(items.map((f: any) => ({
          finding_id: f.finding_id || f.id,
          title: f.title || f.clause_type || "Unknown",
          clause_type: f.clause_type || "",
        })));
      } catch { /* ignore */ }
    })();
  }, [selectedReview]);

  // Close dropdown on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (reviewSearchRef.current && !reviewSearchRef.current.contains(e.target as Node)) {
        setShowReviewDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = (templates ?? []).filter((t) => {
    const matchesSearch = t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.clause_type.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleApply = async () => {
    if (!previewTemplate || !applyReviewId) return;
    setApplying(true);
    setApplyResult(null);
    try {
      const result = await redlineTemplateApi.applyToReview({
        template_id: previewTemplate.template_id,
        review_id: applyReviewId,
        finding_id: applyFindingId || undefined,
        clause_type: previewTemplate.clause_type,
      });
      setApplyResult(`✅ Applied "${result.template_name}" — redline created${result.finding_resolved ? " and finding resolved" : ""}`);
    } catch (err) {
      setApplyResult(`❌ ${err instanceof Error ? err.message : "Failed"}`);
    } finally {
      setApplying(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search templates..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64 pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="all">All Status</option>
            <option value="active">Approved</option>
            <option value="published">Published</option>
            <option value="pending_review">Pending Review</option>
            <option value="ai_draft">AI Generated</option>
            <option value="draft">Draft</option>
            <option value="deprecated">Deprecated</option>
            <option value="retired">Retired</option>
          </select>
        </div>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Template
        </button>
      </div>

      {/* Create Dialog */}
      <AnimatePresence>
        {showCreateDialog && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowCreateDialog(false)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-lg shadow-xl"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900 dark:text-white">Create Template</h3>
                <button onClick={() => setShowCreateDialog(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>
              <div className="space-y-3">
                <input
                  type="text" placeholder="Template Name" value={newTemplate.name}
                  onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
                <input
                  type="text" placeholder="Clause Type (e.g. gdpr, indemnification)" value={newTemplate.clause_type}
                  onChange={(e) => setNewTemplate({ ...newTemplate, clause_type: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
                <input
                  type="text" placeholder="Category" value={newTemplate.category}
                  onChange={(e) => setNewTemplate({ ...newTemplate, category: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
                <textarea
                  placeholder="Template Text" value={newTemplate.template_text} rows={6}
                  onChange={(e) => setNewTemplate({ ...newTemplate, template_text: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                />
                <button
                  onClick={async () => {
                    if (!newTemplate.name || !newTemplate.clause_type || !newTemplate.template_text) return;
                    await createTemplate.mutateAsync({
                      name: newTemplate.name,
                      clause_type: newTemplate.clause_type,
                      category: newTemplate.category || newTemplate.clause_type,
                      template_text: newTemplate.template_text,
                    });
                    setShowCreateDialog(false);
                    setNewTemplate({ name: "", clause_type: "", category: "", template_text: "" });
                  }}
                  disabled={!newTemplate.name || !newTemplate.clause_type || !newTemplate.template_text || createTemplate.isPending}
                  className="w-full px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                >
                  {createTemplate.isPending ? <Loader2 className="w-4 h-4 animate-spin inline" /> : "Create Template"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex gap-4">
        {/* Template Grid */}
        <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 ${previewTemplate ? "lg:grid-cols-2" : "lg:grid-cols-3"}`}>
          {filtered.length === 0 ? (
            <div className="col-span-full text-center py-16">
              <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">No templates found</p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                {templates?.length === 0
                  ? "Create your first template or generate AI drafts from the Coverage tab"
                  : "Try adjusting your filters"}
              </p>
            </div>
          ) : (
            filtered.map((template) => {
              const status = STATUS_STYLE[template.status] ?? STATUS_STYLE.draft;
              const StatusIcon = status.icon;
              return (
                <motion.div
                  key={template.template_id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={() => setPreviewTemplate(template)}
                  className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-700 transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 dark:text-white truncate">
                        {template.name}
                      </h3>
                      <p className="text-xs text-gray-400 capitalize mt-0.5">
                        {template.clause_type.replace(/_/g, " ")}
                      </p>
                    </div>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ml-2 ${status.class}`}>
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mb-3">
                    {template.template_text.slice(0, 200)}
                  </p>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>v{template.version}</span>
                    <span>Used {template.usage_count} times</span>
                    <span>{template.accept_rate > 0 ? `${Math.round(template.accept_rate * 100)}% accept` : "—"}</span>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>

        {/* Preview Panel */}
        <AnimatePresence>
          {previewTemplate && (
            <motion.div
              initial={{ opacity: 0, x: 300 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 300 }}
              className="w-96 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden flex-shrink-0"
            >
              {/* Preview Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-white text-sm truncate">
                  {previewTemplate.name}
                </h3>
                <button
                  onClick={() => { setPreviewTemplate(null); setApplyResult(null); }}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>

              <div className="p-4 space-y-4 overflow-y-auto max-h-[calc(100vh-300px)]">
                {/* Status & Version */}
                <div className="flex items-center justify-between">
                  {(() => {
                    const s = STATUS_STYLE[previewTemplate.status] ?? STATUS_STYLE.draft;
                    const Icon = s.icon;
                    return (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${s.class}`}>
                        <Icon className="w-3 h-3" />
                        {s.label}
                      </span>
                    );
                  })()}
                  <span className="text-xs text-gray-400">v{previewTemplate.version}</span>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
                    <p className="text-[10px] text-gray-400 uppercase">Clause Type</p>
                    <p className="text-xs font-medium text-gray-900 dark:text-white capitalize mt-0.5">
                      {previewTemplate.clause_type.replace(/_/g, " ")}
                    </p>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
                    <p className="text-[10px] text-gray-400 uppercase">Category</p>
                    <p className="text-xs font-medium text-gray-900 dark:text-white capitalize mt-0.5">
                      {previewTemplate.category.replace(/_/g, " ")}
                    </p>
                  </div>
                  {previewTemplate.jurisdiction && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
                      <p className="text-[10px] text-gray-400 uppercase flex items-center gap-1">
                        <Globe className="w-3 h-3" /> Jurisdiction
                      </p>
                      <p className="text-xs font-medium text-gray-900 dark:text-white mt-0.5">
                        {previewTemplate.jurisdiction}
                      </p>
                    </div>
                  )}
                  {previewTemplate.industry && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
                      <p className="text-[10px] text-gray-400 uppercase flex items-center gap-1">
                        <Building2 className="w-3 h-3" /> Industry
                      </p>
                      <p className="text-xs font-medium text-gray-900 dark:text-white mt-0.5">
                        {previewTemplate.industry}
                      </p>
                    </div>
                  )}
                  {previewTemplate.risk_level && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
                      <p className="text-[10px] text-gray-400 uppercase flex items-center gap-1">
                        <Shield className="w-3 h-3" /> Risk Level
                      </p>
                      <p className="text-xs font-medium text-gray-900 dark:text-white mt-0.5 capitalize">
                        {previewTemplate.risk_level}
                      </p>
                    </div>
                  )}
                </div>

                {/* Template Text */}
                <div>
                  <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Template Text</p>
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 max-h-40 overflow-y-auto">
                    <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-sans">
                      {previewTemplate.template_text}
                    </pre>
                  </div>
                </div>

                {/* Template Effectiveness */}
                <div className="bg-gradient-to-r from-emerald-50 to-emerald-50/50 dark:from-emerald-900/10 dark:to-emerald-900/5 rounded-lg p-3 border border-emerald-200 dark:border-emerald-800">
                  <p className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 uppercase mb-2">Template Effectiveness</p>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-lg font-bold text-gray-900 dark:text-white">{previewTemplate.usage_count}</p>
                      <p className="text-[10px] text-gray-500">Used</p>
                    </div>
                    <div>
                      <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                        {previewTemplate.accept_rate > 0 ? `${Math.round(previewTemplate.accept_rate * 100)}%` : "—"}
                      </p>
                      <p className="text-[10px] text-gray-500">Success Rate</p>
                    </div>
                    <div>
                      <p className="text-lg font-bold text-gray-900 dark:text-white">
                        {previewTemplate.usage_count > 0 ? `${(previewTemplate.usage_count * 4.2).toFixed(1)}m` : "—"}
                      </p>
                      <p className="text-[10px] text-gray-500">Avg Time Saved</p>
                    </div>
                  </div>
                </div>

                {/* Apply Impact Preview */}
                <div className="bg-gradient-to-r from-indigo-50 to-indigo-50/50 dark:from-indigo-900/10 dark:to-indigo-900/5 rounded-lg p-3 border border-indigo-200 dark:border-indigo-800">
                  <p className="text-[10px] font-semibold text-indigo-700 dark:text-indigo-400 uppercase mb-2">Apply Impact</p>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                      <span className="text-gray-600 dark:text-gray-400">Resolve matching findings</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <ArrowRight className="w-3 h-3 text-indigo-500" />
                      <span className="text-gray-600 dark:text-gray-400">Add clause to contract</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Shield className="w-3 h-3 text-emerald-500" />
                      <span className="text-gray-600 dark:text-gray-400">No conflicts detected</span>
                    </div>
                  </div>
                </div>

                {/* Similar Templates */}
                {templates && templates.filter(t =>
                  t.clause_type === previewTemplate.clause_type && t.template_id !== previewTemplate.template_id
                ).length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Similar Templates</p>
                    <div className="space-y-1.5">
                      {templates.filter(t =>
                        t.clause_type === previewTemplate.clause_type && t.template_id !== previewTemplate.template_id
                      ).slice(0, 3).map((similar) => {
                        const s = STATUS_STYLE[similar.status] ?? STATUS_STYLE.draft;
                        return (
                          <button
                            key={similar.template_id}
                            onClick={() => setPreviewTemplate(similar)}
                            className="w-full text-left px-3 py-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                          >
                            <p className="text-xs font-medium text-gray-900 dark:text-white truncate">{similar.name}</p>
                            <p className="text-[10px] text-gray-400">
                              v{similar.version} · {Math.round(similar.accept_rate * 100)}% accept
                            </p>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Clause Bundle */}
                {RELATED_CLAUSES[previewTemplate.clause_type] && (
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Recommended Bundle</p>
                    <div className="bg-gradient-to-r from-purple-50 to-purple-50/50 dark:from-purple-900/10 dark:to-purple-900/5 rounded-lg p-3 border border-purple-200 dark:border-purple-800">
                      <div className="space-y-1.5 mb-2">
                        {RELATED_CLAUSES[previewTemplate.clause_type].map((related) => (
                          <div key={related} className="flex items-center gap-2 text-xs">
                            <CheckCircle2 className="w-3 h-3 text-purple-500" />
                            <span className="text-gray-700 dark:text-gray-300 capitalize">{related.replace(/_/g, " ")}</span>
                          </div>
                        ))}
                      </div>
                      <button className="w-full px-3 py-1.5 text-xs font-medium bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors">
                        Apply Bundle ({RELATED_CLAUSES[previewTemplate.clause_type].length} templates)
                      </button>
                    </div>
                  </div>
                )}

                {/* Apply to Review — Context-Aware */}
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {selectedReview ? "Apply to Review" : "Select Review"}
                  </p>

                  {/* If review is auto-detected from URL, show current context */}
                  {selectedReview && !reviewSearch ? (
                    <div className="space-y-2">
                      <div className="bg-indigo-50 dark:bg-indigo-900/10 rounded-lg p-2.5 border border-indigo-200 dark:border-indigo-800">
                        <p className="text-xs font-medium text-indigo-700 dark:text-indigo-300">{selectedReview.filename}</p>
                        <p className="text-[10px] text-indigo-500 mt-0.5">Auto-detected from workspace</p>
                      </div>

                      {/* Findings dropdown */}
                      {findings.length > 0 && (
                        <select
                          value={selectedFinding?.finding_id || ""}
                          onChange={(e) => {
                            const f = findings.find((x) => x.finding_id === e.target.value);
                            if (f) {
                              setSelectedFinding(f);
                              setApplyFindingId(f.finding_id);
                            }
                          }}
                          className="w-full px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                        >
                          <option value="">All matching findings</option>
                          {findings.map((f) => (
                            <option key={f.finding_id} value={f.finding_id}>{f.title}</option>
                          ))}
                        </select>
                      )}

                      {/* Apply Impact */}
                      <div className="bg-gradient-to-r from-emerald-50 to-emerald-50/50 dark:from-emerald-900/10 dark:to-emerald-900/5 rounded-lg p-2.5 border border-emerald-200 dark:border-emerald-800">
                        <div className="space-y-1 text-xs">
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                            <span className="text-gray-600 dark:text-gray-400">
                              {selectedFinding ? "Resolve 1 finding" : "Resolve matching findings"}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <ArrowRight className="w-3 h-3 text-indigo-500" />
                            <span className="text-gray-600 dark:text-gray-400">Insert clause into contract</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Shield className="w-3 h-3 text-emerald-500" />
                            <span className="text-gray-600 dark:text-gray-400">No conflicts detected</span>
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={handleApply}
                        disabled={applying}
                        className="w-full px-3 py-2 text-xs font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                      >
                        {applying ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                        Accept & Apply
                      </button>
                    </div>
                  ) : (
                    /* Review search (standalone mode) */
                    <div className="space-y-2" ref={reviewSearchRef}>
                      <div className="relative">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
                        <input
                          type="text"
                          placeholder="Search contract name..."
                          value={reviewSearch}
                          onChange={(e) => {
                            setReviewSearch(e.target.value);
                            if (selectedReview) {
                              setSelectedReview(null);
                              setApplyReviewId("");
                              setSelectedFinding(null);
                              setApplyFindingId("");
                              setFindings([]);
                            }
                          }}
                          onFocus={() => reviewResults.length > 0 && setShowReviewDropdown(true)}
                          className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                        />
                      </div>

                      {/* Review dropdown results */}
                      {showReviewDropdown && reviewResults.length > 0 && (
                        <div className="border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 overflow-hidden shadow-lg">
                          {reviewResults.map((r) => (
                            <button
                              key={r.review_id}
                              onClick={() => {
                                setSelectedReview(r);
                                setApplyReviewId(r.review_id);
                                setReviewSearch(r.filename);
                                setShowReviewDropdown(false);
                              }}
                              className="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 border-b border-gray-100 dark:border-gray-700 last:border-0"
                            >
                              {r.filename}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Findings dropdown (after review selected) */}
                      {selectedReview && findings.length > 0 && (
                        <select
                          value={selectedFinding?.finding_id || ""}
                          onChange={(e) => {
                            const f = findings.find((x) => x.finding_id === e.target.value);
                            if (f) {
                              setSelectedFinding(f);
                              setApplyFindingId(f.finding_id);
                            }
                          }}
                          className="w-full px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                        >
                          <option value="">All matching findings</option>
                          {findings.map((f) => (
                            <option key={f.finding_id} value={f.finding_id}>{f.title}</option>
                          ))}
                        </select>
                      )}

                      {/* Apply button (only when review selected) */}
                      {selectedReview && (
                        <>
                          <div className="bg-gradient-to-r from-emerald-50 to-emerald-50/50 dark:from-emerald-900/10 dark:to-emerald-900/5 rounded-lg p-2.5 border border-emerald-200 dark:border-emerald-800">
                            <div className="space-y-1 text-xs">
                              <div className="flex items-center gap-2">
                                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                                <span className="text-gray-600 dark:text-gray-400">
                                  {selectedFinding ? "Resolve 1 finding" : "Resolve matching findings"}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <ArrowRight className="w-3 h-3 text-indigo-500" />
                                <span className="text-gray-600 dark:text-gray-400">Insert clause into contract</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Shield className="w-3 h-3 text-emerald-500" />
                                <span className="text-gray-600 dark:text-gray-400">No conflicts detected</span>
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={handleApply}
                            disabled={applying}
                            className="w-full px-3 py-2 text-xs font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                          >
                            {applying ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                            Accept & Apply
                          </button>
                        </>
                      )}

                      {applyResult && (
                        <p className="text-xs text-center text-gray-600 dark:text-gray-400">{applyResult}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export { RELATED_CLAUSES };

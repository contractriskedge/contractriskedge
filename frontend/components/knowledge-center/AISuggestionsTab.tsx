/**
 * AI Suggestions tab — missing templates ranked by frequency with one-click generation.
 */
"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lightbulb,
  Loader2,
  FilePlus2,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Eye,
  X,
  ArrowRight,
  FileCheck,
  Search,
} from "lucide-react";
import { useMissingTemplates, useGenerateDraft } from "@/services/hooks/useRedlineTemplates";
import { redlineTemplateApi } from "@/services/api/redlineTemplates";
import type { MissingTemplate, AIDraftResponse } from "@/services/api/redlineTemplates";

export function AISuggestionsTab() {
  const { data: missing, isLoading } = useMissingTemplates(50);
  const generateDraft = useGenerateDraft();
  const [generating, setGenerating] = useState<string | null>(null);
  const [draft, setDraft] = useState<{ clause: string; response: AIDraftResponse } | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<string | null>(null);
  const [showApplyForm, setShowApplyForm] = useState(false);

  // Context-aware review selection
  const [reviewSearch, setReviewSearch] = useState("");
  const [reviewResults, setReviewResults] = useState<{ review_id: string; filename: string }[]>([]);
  const [selectedReview, setSelectedReview] = useState<{ review_id: string; filename: string } | null>(null);
  const [showReviewDropdown, setShowReviewDropdown] = useState(false);
  const [findings, setFindings] = useState<{ finding_id: string; title: string; clause_type: string }[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<{ finding_id: string; title: string } | null>(null);
  const reviewSearchRef = useRef<HTMLDivElement>(null);

  // Auto-detect from URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const rid = params.get("review_id");
    const fid = params.get("finding_id");
    if (rid) {
      setSelectedReview({ review_id: rid, filename: "Current Review" });
    }
    if (fid) {
      setSelectedFinding({ finding_id: fid, title: "Current Finding" });
    }
  }, []);

  // Search reviews
  useEffect(() => {
    if (reviewSearch.length < 2) { setReviewResults([]); return; }
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

  // Load findings when review selected
  useEffect(() => {
    if (!selectedReview) return;
    (async () => {
      try {
        const { reviewService } = await import("@/services/api/reviews");
        await reviewService.get(selectedReview.review_id);
        const findingsResp = await (await import("@/services/api/client")).api.get(`/reviews/${selectedReview.review_id}/findings`);
        const items = findingsResp?.findings || [];
        setFindings(items.map((f: any) => ({
          finding_id: f.finding_id || f.id,
          title: f.title || f.clause_type || "Unknown",
          clause_type: f.clause_type || "",
        })));
      } catch { /* ignore */ }
    })();
  }, [selectedReview]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (reviewSearchRef.current && !reviewSearchRef.current.contains(e.target as Node)) {
        setShowReviewDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleGenerate = async (item: MissingTemplate) => {
    setGenerating(item.clause_type);
    setApplyResult(null);
    try {
      const response = await generateDraft.mutateAsync({
        clause_type: item.clause_type,
        finding_title: `Missing ${item.clause_type.replace(/_/g, " ")} Clause`,
        finding_description: `${item.findings} findings detected across ${item.first_seen ? "regression suite" : "contracts"}`,
      });
      setDraft({ clause: item.clause_type, response });
      setShowApplyForm(false);
    } catch {
      alert("Failed to generate draft. Check API key.");
    } finally {
      setGenerating(null);
    }
  };

  const handleApply = async () => {
    if (!draft || !selectedReview) {
      alert("Please search and select a review first");
      return;
    }
    setApplying(true);
    setApplyResult(null);
    try {
      // First promote to template
      const template = await redlineTemplateApi.promoteToTemplate({
        draft_text: draft.response.draft_text,
        name: `${draft.clause.replace(/_/g, " ")} Clause`,
        clause_type: draft.clause,
        category: draft.clause,
      });

      // Then apply to review
      const result = await redlineTemplateApi.applyToReview({
        template_id: template.template_id,
        review_id: selectedReview.review_id,
        finding_id: selectedFinding?.finding_id,
        clause_type: draft.clause,
      });

      setApplyResult(`✅ Applied "${result.template_name}" to "${selectedReview.filename}" — redline created${result.finding_resolved ? " and finding resolved" : ""}`);
      setShowApplyForm(false);
    } catch (err) {
      setApplyResult(`❌ Failed: ${err instanceof Error ? err.message : "Unknown error"}`);
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
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">
            AI-Generated Template Suggestions
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Missing clause types ranked by frequency — generate enterprise templates with one click
          </p>
        </div>
        <button
          disabled={!missing || missing.length === 0}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
          onClick={async () => {
            if (!missing) return;
            for (const item of missing.slice(0, 5)) {
              await handleGenerate(item);
            }
            alert("Batch generation complete! Check Templates tab.");
          }}
        >
          <Sparkles className="w-4 h-4" />
          Generate Top 5
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Missing List */}
        <div className="space-y-2">
          {(missing ?? []).map((item, i) => (
            <motion.div
              key={item.clause_type}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium text-gray-400 w-5">{i + 1}.</span>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                    {item.clause_type.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-gray-400">{item.findings} findings</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">{item.findings} findings</span>
                <button
                  onClick={() => handleGenerate(item)}
                  disabled={generating === item.clause_type}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-md hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors disabled:opacity-50"
                >
                  {generating === item.clause_type ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <FilePlus2 className="w-3 h-3" />
                  )}
                  Generate
                </button>
              </div>
            </motion.div>
          ))}
          {(!missing || missing.length === 0) && (
            <div className="text-center py-12 text-gray-400">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
              <p>All clause types have templates!</p>
            </div>
          )}
        </div>

        {/* Draft Preview */}
        <AnimatePresence>
          {draft && (
            <motion.div
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 16 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-purple-200 dark:border-purple-800 p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-500" />
                  <h4 className="font-medium text-gray-900 dark:text-white capitalize">
                    {draft.clause.replace(/_/g, " ")}
                  </h4>
                </div>
                <button
                  onClick={() => setDraft(null)}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>

              {/* Confidence & Matching Score */}
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div className="bg-purple-50 dark:bg-purple-900/10 rounded-lg p-3">
                  <p className="text-xs text-purple-600 dark:text-purple-400 mb-1">
                    AI Confidence
                  </p>
                  <p className="text-lg font-bold text-purple-700 dark:text-purple-300">
                    {Math.round((draft.response.provenance?.confidence ?? draft.response.confidence) * 100)}%
                  </p>
                  <div className="mt-2 space-y-1">
                    {(draft.response.provenance?.sources ?? []).map((s) => (
                      <div key={s.type} className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">{s.label}</span>
                        <span className="font-medium text-gray-700 dark:text-gray-300">{s.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-indigo-50 dark:bg-indigo-900/10 rounded-lg p-3">
                  <p className="text-xs text-indigo-600 dark:text-indigo-400 mb-1">
                    Matching Score
                  </p>
                  <p className="text-lg font-bold text-indigo-700 dark:text-indigo-300">
                    {Math.round((draft.response.provenance?.matching_score ?? 0) * 100)}%
                  </p>
                  <div className="mt-2 space-y-1">
                    {(draft.response.provenance?.factors ?? []).map((f) => (
                      <div key={f.name} className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">{f.name}</span>
                        <span className="font-medium text-gray-700 dark:text-gray-300">
                          {Math.round(f.score * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="bg-purple-50 dark:bg-purple-900/10 rounded-lg p-3 mb-3">
                <p className="text-xs text-purple-600 dark:text-purple-400 mb-1">
                  AI Generated — {draft.response.model_used}
                </p>
                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {draft.response.draft_text}
                </p>
              </div>
              <div className="flex flex-col gap-2">
                {/* Action buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowApplyForm(true)}
                    className="flex-1 px-3 py-2 text-sm font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
                  >
                    <CheckCircle2 className="w-4 h-4 inline mr-1" />
                    Accept & Apply to Review
                  </button>
                  <button
                    onClick={async () => {
                      try {
                        await redlineTemplateApi.promoteToTemplate({
                          draft_text: draft.response.draft_text,
                          name: `${draft.clause.replace(/_/g, " ")} Clause`,
                          clause_type: draft.clause,
                          category: draft.clause,
                        });
                        setApplyResult("✅ Saved as enterprise template!");
                      } catch {
                        setApplyResult("❌ Failed to save template");
                      }
                    }}
                    className="px-3 py-2 text-sm font-medium border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <FileCheck className="w-4 h-4" />
                  </button>
                </div>

                {/* Apply form */}
                <AnimatePresence>
                  {showApplyForm && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 space-y-2" ref={reviewSearchRef}>
                        <p className="text-xs font-medium text-gray-600 dark:text-gray-400">
                          Select Review
                        </p>

                        {/* Review search */}
                        <div className="relative">
                          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
                          <input
                            type="text"
                            placeholder="Search contract name..."
                            value={selectedReview ? selectedReview.filename : reviewSearch}
                            onChange={(e) => {
                              setReviewSearch(e.target.value);
                              setSelectedReview(null);
                              setSelectedFinding(null);
                              setFindings([]);
                            }}
                            onFocus={() => reviewResults.length > 0 && setShowReviewDropdown(true)}
                            className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                          />
                        </div>

                        {/* Dropdown */}
                        {showReviewDropdown && reviewResults.length > 0 && (
                          <div className="border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 overflow-hidden shadow-lg">
                            {reviewResults.map((r) => (
                              <button
                                key={r.review_id}
                                onClick={() => {
                                  setSelectedReview(r);
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

                        {/* Findings dropdown */}
                        {selectedReview && findings.length > 0 && (
                          <select
                            value={selectedFinding?.finding_id || ""}
                            onChange={(e) => {
                              const f = findings.find((x) => x.finding_id === e.target.value);
                              if (f) setSelectedFinding(f);
                            }}
                            className="w-full px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                          >
                            <option value="">All matching findings</option>
                            {findings.map((f) => (
                              <option key={f.finding_id} value={f.finding_id}>{f.title}</option>
                            ))}
                          </select>
                        )}

                        {/* Apply button */}
                        {selectedReview && (
                          <button
                            onClick={handleApply}
                            disabled={applying}
                            className="w-full px-3 py-1.5 text-xs font-medium bg-emerald-600 text-white rounded hover:bg-emerald-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                          >
                            {applying ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <CheckCircle2 className="w-3 h-3" />
                            )}
                            Apply to "{selectedReview.filename}"
                          </button>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Result message */}
                {applyResult && (
                  <div className="text-xs text-center py-1 px-2 bg-gray-50 dark:bg-gray-700/50 rounded">
                    {applyResult}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

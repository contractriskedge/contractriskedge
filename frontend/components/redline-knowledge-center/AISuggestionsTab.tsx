/**
 * AI Suggestions tab — missing templates ranked by frequency with one-click generation.
 */
"use client";

import React, { useState } from "react";
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
} from "lucide-react";
import { useMissingTemplates, useGenerateDraft } from "@/services/hooks/useRedlineTemplates";
import type { MissingTemplate, AIDraftResponse } from "@/services/api/redlineTemplates";

export function AISuggestionsTab() {
  const { data: missing, isLoading } = useMissingTemplates(50);
  const generateDraft = useGenerateDraft();
  const [generating, setGenerating] = useState<string | null>(null);
  const [draft, setDraft] = useState<{ clause: string; response: AIDraftResponse } | null>(null);

  const handleGenerate = async (item: MissingTemplate) => {
    setGenerating(item.clause_type);
    try {
      const response = await generateDraft.mutateAsync({
        clause_type: item.clause_type,
        finding_title: `Missing ${item.clause_type.replace(/_/g, " ")} Clause`,
        finding_description: `${item.findings} findings detected across ${item.first_seen ? "regression suite" : "contracts"}`,
      });
      setDraft({ clause: item.clause_type, response });
    } catch {
      alert("Failed to generate draft. Check API key.");
    } finally {
      setGenerating(null);
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
              <div className="bg-purple-50 dark:bg-purple-900/10 rounded-lg p-3 mb-3">
                <p className="text-xs text-purple-600 dark:text-purple-400 mb-1">
                  AI Generated — Confidence: {Math.round(draft.response.confidence * 100)}%
                </p>
                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {draft.response.draft_text}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button className="flex-1 px-3 py-2 text-sm font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
                  <CheckCircle2 className="w-4 h-4 inline mr-1" />
                  Accept & Save as Template
                </button>
                <button className="px-3 py-2 text-sm font-medium border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                  <Eye className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

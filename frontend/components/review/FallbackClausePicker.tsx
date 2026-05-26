/**
 * FallbackClausePicker — displays approved/preferred/fallback clause language
 * from the company playbook for a given clause type.
 *
 * Used inside the RedlineEditModal to let reviewers see and select
 * company-approved language when editing a redline.
 */

"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Check, ChevronDown, ChevronRight, Shield, AlertTriangle, Loader2 } from "lucide-react";
import { reviewService } from "@/services/api/reviews";
import type { FallbackRecommendation } from "@/services/api/client";

interface FallbackClausePickerProps {
  clauseType: string | null;
  onSelectFallback: (text: string) => void;
  currentText: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

function ClauseTypeBadge({ clauseType }: { clauseType: string }) {
  const colors: Record<string, string> = {
    approved: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    preferred: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    fallback: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  };
  return (
    <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${colors[clauseType] || "bg-gray-100 text-gray-600"}`}>
      {clauseType}
    </span>
  );
}

export function FallbackClausePicker({ clauseType, onSelectFallback, currentText }: FallbackClausePickerProps) {
  const [expanded, setExpanded] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["playbook", "fallback", clauseType],
    queryFn: async () => {
      if (!clauseType) return null;
      const res = await fetch(`${API_BASE}/playbooks/fallback?clause_type=${encodeURIComponent(clauseType)}`);
      if (!res.ok) return null;
      return res.json() as Promise<{
        clause_category: string;
        recommendations: FallbackRecommendation[];
        has_approved: boolean;
        has_preferred: boolean;
        has_fallback: boolean;
      }>;
    },
    enabled: Boolean(clauseType) && expanded,
    staleTime: 60_000,
  });

  if (!clauseType) return null;

  const hasContent = data && data.recommendations.length > 0;

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/50 overflow-hidden dark:border-blue-800 dark:bg-blue-900/10">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left transition-colors hover:bg-blue-100/50 dark:hover:bg-blue-900/20"
      >
        <BookOpen className="w-4 h-4 text-blue-500" />
        <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">
          Company Playbook
        </span>
        {data && (
          <div className="flex items-center gap-1.5 ml-2">
            {data.has_approved && (
              <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                {data.recommendations.filter(r => r.clause_type === "approved").length} approved
              </span>
            )}
            {data.has_preferred && (
              <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                preferred
              </span>
            )}
          </div>
        )}
        <div className="ml-auto">
          {expanded ? <ChevronDown className="w-3.5 h-3.5 text-blue-400" /> : <ChevronRight className="w-3.5 h-3.5 text-blue-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-3">
          {isLoading && (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
              <span className="ml-2 text-xs text-blue-500">Loading playbook clauses...</span>
            </div>
          )}

          {error && (
            <p className="text-xs text-red-500 py-2">Failed to load playbook clauses.</p>
          )}

          {!isLoading && !error && !hasContent && (
            <p className="text-xs text-gray-500 dark:text-gray-400 py-2">
              No approved/preferred language found for &ldquo;{clauseType.replace(/_/g, " ")}&rdquo; in the company playbook.
            </p>
          )}

          {hasContent && (
            <div className="space-y-2 mt-1 max-h-64 overflow-y-auto">
              {data.recommendations.map((rec) => (
                <div
                  key={rec.clause_id}
                  className={`rounded-lg border p-3 transition-all cursor-pointer ${
                    selectedId === rec.clause_id
                      ? "border-blue-400 bg-blue-100 dark:border-blue-600 dark:bg-blue-900/30"
                      : "border-blue-200 bg-white hover:border-blue-300 dark:border-blue-700 dark:bg-gray-800"
                  }`}
                  onClick={() => {
                    setSelectedId(rec.clause_id);
                    onSelectFallback(rec.body);
                  }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="text-xs font-semibold text-gray-800 dark:text-gray-200">{rec.title}</h4>
                        <ClauseTypeBadge clauseType={rec.clause_type} />
                      </div>
                      <p className="text-[11px] text-gray-600 dark:text-gray-400 leading-relaxed line-clamp-3">
                        {rec.body}
                      </p>
                      {rec.summary && (
                        <p className="text-[10px] text-blue-600 dark:text-blue-400 mt-1 italic">
                          {rec.summary}
                        </p>
                      )}
                    </div>
                    {selectedId === rec.clause_id && (
                      <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                        <Check className="w-3 h-3 text-white" />
                      </div>
                    )}
                  </div>
                  {rec.risk_level && rec.risk_level !== "medium" && (
                    <div className="flex items-center gap-1 mt-1.5">
                      {rec.risk_level === "critical" || rec.risk_level === "high" ? (
                        <AlertTriangle className="w-2.5 h-2.5 text-red-500" />
                      ) : (
                        <Shield className="w-2.5 h-2.5 text-amber-500" />
                      )}
                      <span className="text-[9px] text-gray-400">{rec.risk_level} risk</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {selectedId && (
            <p className="mt-2 text-[10px] text-blue-600 dark:text-blue-400">
              ✓ Selected. The proposed text will be replaced with this playbook language.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
